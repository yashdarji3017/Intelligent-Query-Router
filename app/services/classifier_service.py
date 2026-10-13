import asyncio
import time
from typing import Optional, Tuple

from app.agents.classifier import (
    ClassifierAgentProtocol,
    get_classifier_agent,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import (
    ClassificationError,
    ProviderError,
    ProviderTimeoutError,
    RateLimitError,
)
from app.core.logger import get_logger
from app.schemas.classification import QueryClassification

logger = get_logger(__name__)


class ClassifierService:
    """
    Coordinate query classification through the configured classifier agent.

    Applies request timeouts, retries transient provider failures with
    exponential backoff, validates classification results, and measures
    classification latency.
    """

    def __init__(
        self,
        classifier_agent: Optional[ClassifierAgentProtocol] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        """
        Initialize the classifier service.

        Args:
            classifier_agent: Optional classifier implementation, useful for
                dependency injection and testing.
            settings: Optional application settings controlling timeouts,
                retries, and retry backoff.
        """
        self.settings = settings or get_settings()
        self._classifier_agent = classifier_agent

    @property
    def classifier_agent(self) -> ClassifierAgentProtocol:
        """
        Return the configured classifier agent, initializing it lazily.

        Returns:
            ClassifierAgentProtocol: Agent used to classify user queries.
        """
        if self._classifier_agent is None:
            self._classifier_agent = get_classifier_agent(self.settings)

        return self._classifier_agent

    async def classify_query(
        self,
        query: str,
    ) -> Tuple[QueryClassification, float]:
        """
        Classify a query with timeout handling and bounded retries.

        Retries transient provider failures and timeouts according to the
        configured retry policy. Invalid classification results and known
        application exceptions are propagated without unnecessary retries.

        Args:
            query: Non-empty user query to classify.

        Returns:
            Tuple[QueryClassification, float]: Validated classification
            result and elapsed classification time in milliseconds.

        Raises:
            ClassificationError: If the output is invalid or classification
                validation fails.
            ProviderTimeoutError: If all classification attempts time out.
            RateLimitError: If the provider rate limit is exhausted.
            ProviderError: If classification fails after all retries.
        """
        if not isinstance(query, str) or not query.strip():
            raise ClassificationError(
                "Query must be a non-empty string."
            )

        start_time = time.perf_counter()
        retries = self.settings.max_retries
        timeout_seconds = self.settings.request_timeout_seconds
        backoff_base = self.settings.retry_backoff_base_seconds

        for attempt in range(retries + 1):
            try:
                classification = await asyncio.wait_for(
                    self.classifier_agent.classify(query),
                    timeout=timeout_seconds,
                )

                if not isinstance(classification, QueryClassification):
                    raise ClassificationError(
                        "Classifier returned an invalid output type: "
                        f"{type(classification).__name__}."
                    )

                latency_ms = (
                    time.perf_counter() - start_time
                ) * 1000.0

                logger.info(
                    "Query classified successfully: attempt=%d, "
                    "category=%s, confidence=%.2f, latency_ms=%.1f",
                    attempt + 1,
                    classification.category,
                    classification.confidence,
                    latency_ms,
                )

                return classification, latency_ms

            except asyncio.TimeoutError as exc:
                logger.warning(
                    "Classifier attempt timed out: attempt=%d, "
                    "timeout_seconds=%.1f",
                    attempt + 1,
                    timeout_seconds,
                )

                if attempt == retries:
                    raise ProviderTimeoutError(
                        "Classification timed out after "
                        f"{retries + 1} attempts."
                    ) from exc

            except (
                ClassificationError,
                ProviderTimeoutError,
                RateLimitError,
            ):
                raise

            except Exception as exc:
                error_message = str(exc).lower()

                is_rate_limited = any(
                    indicator in error_message
                    for indicator in (
                        "429",
                        "quota",
                        "resource_exhausted",
                        "rate limit",
                        "too many requests",
                    )
                )

                if is_rate_limited:
                    logger.warning(
                        "Provider rate limit encountered: attempt=%d, "
                        "error_type=%s",
                        attempt + 1,
                        type(exc).__name__,
                    )

                    if attempt == retries:
                        raise RateLimitError() from exc

                elif isinstance(exc, (ValueError, TypeError)):
                    logger.exception(
                        "Invalid classifier output: error_type=%s",
                        type(exc).__name__,
                    )
                    raise ClassificationError(
                        "Classifier returned an invalid output format."
                    ) from exc

                else:
                    logger.warning(
                        "Classifier attempt failed: attempt=%d, "
                        "error_type=%s",
                        attempt + 1,
                        type(exc).__name__,
                    )

                    if attempt == retries:
                        raise ProviderError(
                            "Classification failed due to a provider error."
                        ) from exc

            if attempt < retries:
                backoff_seconds = backoff_base * (2 ** attempt)

                logger.debug(
                    "Retrying classification: next_attempt=%d, "
                    "backoff_seconds=%.2f",
                    attempt + 2,
                    backoff_seconds,
                )

                await asyncio.sleep(backoff_seconds)

        raise ProviderError("Classification failed.")