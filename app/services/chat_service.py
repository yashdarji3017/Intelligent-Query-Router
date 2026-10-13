import asyncio
import time
import uuid
from typing import Optional

from app.core.config import Settings, get_settings
from app.core.exceptions import (
    AppBaseException,
    ClassificationError,
    HandlerExecutionError,
    ProviderTimeoutError,
)
from app.core.logger import get_logger
from app.schemas.response import ChatResponse, ClassificationResponse
from app.services.classifier_service import ClassifierService
from app.services.router_service import DeterministicRouter

logger = get_logger(__name__)


class ChatService:
    """
    Coordinate query classification, deterministic routing, and response
    generation.

    Controls concurrent request processing, enforces handler execution
    timeouts, and records request identifiers and latency metrics for
    operational monitoring.
    """

    def __init__(
        self,
        classifier_service: Optional[ClassifierService] = None,
        router: Optional[DeterministicRouter] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        """
        Initialize the chat service and its dependencies.

        Args:
            classifier_service: Optional classifier implementation.
            router: Optional deterministic router for handler selection.
            settings: Optional application configuration.
        """
        self.settings = settings or get_settings()
        self.classifier_service = (
            classifier_service
            or ClassifierService(settings=self.settings)
        )
        self.router = router or DeterministicRouter(
            settings=self.settings,
        )
        self._semaphore = asyncio.Semaphore(
            self.settings.max_concurrent_requests
        )

        logger.info(
            "ChatService initialized: max_concurrent_requests=%d, "
            "request_timeout_seconds=%.1f",
            self.settings.max_concurrent_requests,
            self.settings.request_timeout_seconds,
        )

    def generate_request_id(self) -> str:
        """
        Generate a unique identifier for a request.

        Returns:
            str: Request identifier with a ``req_`` prefix.
        """
        return f"req_{uuid.uuid4().hex[:12]}"

    async def process_chat(
        self,
        query: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> ChatResponse:
        """
        Classify a query, resolve its handler, and generate a response.

        Limits concurrent processing, measures classification and handler
        latency, and converts handler timeouts or unexpected handler failures
        into application-specific exceptions.

        Args:
            query: User query to process.
            user_id: Optional user identifier for request tracing.
            session_id: Optional session identifier for request tracing.

        Returns:
            ChatResponse: Generated answer and classification metadata.

        Raises:
            ClassificationError: If query classification fails.
            ProviderTimeoutError: If classification or handler execution
                exceeds its configured timeout.
            HandlerExecutionError: If handler execution fails unexpectedly.
        """
        request_id = self.generate_request_id()
        total_start = time.perf_counter()

        logger.info(
            "[%s] Chat request started: user_id=%s, session_id=%s, "
            "query_length=%d",
            request_id,
            user_id or "anonymous",
            session_id or "none",
            len(query),
        )

        try:
            async with self._semaphore:
                try:
                    classification, class_latency_ms = (
                        await self.classifier_service.classify_query(query)
                    )
                except AppBaseException:
                    raise
                except Exception as exc:
                    logger.exception(
                        "[%s] Query classification failed.",
                        request_id,
                    )
                    raise ClassificationError(
                        "Failed to classify the query."
                    ) from exc

                logger.info(
                    "[%s] Query classified: category=%s, urgency=%s, "
                    "complexity=%s, confidence=%.2f, latency_ms=%.1f",
                    request_id,
                    classification.category,
                    classification.urgency,
                    classification.complexity,
                    classification.confidence,
                    class_latency_ms,
                )

                resolved_handler = self.router.resolve_target(
                    classification,
                )

                logger.info(
                    "[%s] Handler resolved: target=%s",
                    request_id,
                    resolved_handler,
                )

                handler_start = time.perf_counter()

                try:
                    answer = await asyncio.wait_for(
                        self.router.dispatch(
                            resolved_handler,
                            query,
                            classification,
                        ),
                        timeout=self.settings.request_timeout_seconds,
                    )
                except asyncio.TimeoutError as exc:
                    logger.warning(
                        "[%s] Handler execution timed out: handler=%s, "
                        "timeout_seconds=%.1f",
                        request_id,
                        resolved_handler,
                        self.settings.request_timeout_seconds,
                    )
                    raise ProviderTimeoutError(
                        f"Handler '{resolved_handler}' timed out."
                    ) from exc
                except Exception as exc:
                    logger.exception(
                        "[%s] Handler execution failed: handler=%s",
                        request_id,
                        resolved_handler,
                    )
                    raise HandlerExecutionError(
                        f"Handler '{resolved_handler}' failed to process "
                        "the request."
                    ) from exc

                handler_latency_ms = (
                    time.perf_counter() - handler_start
                ) * 1000.0
                total_latency_ms = (
                    time.perf_counter() - total_start
                ) * 1000.0

                logger.info(
                    "[%s] Chat request completed: handler=%s, "
                    "handler_latency_ms=%.1f, total_latency_ms=%.1f",
                    request_id,
                    resolved_handler,
                    handler_latency_ms,
                    total_latency_ms,
                )

                return ChatResponse(
                    request_id=request_id,
                    category=str(classification.category),
                    urgency=str(classification.urgency),
                    complexity=str(classification.complexity),
                    confidence=classification.confidence,
                    target_agent=resolved_handler,
                    answer=answer,
                    requires_clarification=(
                        classification.requires_clarification
                    ),
                    status="success",
                    total_latency_ms=round(total_latency_ms, 2),
                )

        except (ClassificationError, ProviderTimeoutError, HandlerExecutionError):
            raise
        except Exception:
            logger.exception(
                "[%s] Unexpected chat processing failure.",
                request_id,
            )
            raise

    async def process_classification(
        self,
        query: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> ClassificationResponse:
        """
        Classify a query and resolve its intended handler without execution.

        Runs the classifier and deterministic router, returning the
        classification metadata and measured classification latency.

        Args:
            query: User query to classify.
            user_id: Optional user identifier for request tracing.
            session_id: Optional session identifier for request tracing.

        Returns:
            ClassificationResponse: Classification result and routing target.

        Raises:
            ClassificationError: If classification fails.
            Exception: Propagates unexpected routing or processing failures.
        """
        request_id = self.generate_request_id()
        start_time = time.perf_counter()

        logger.info(
            "[%s] Classification-only request started: "
            "user_id=%s, session_id=%s, query_length=%d",
            request_id,
            user_id or "anonymous",
            session_id or "none",
            len(query),
        )

        try:
            async with self._semaphore:
                try:
                    classification, class_latency_ms = (
                        await self.classifier_service.classify_query(query)
                    )
                except AppBaseException:
                    raise
                except Exception as exc:
                    logger.exception(
                        "[%s] Standalone query classification failed.",
                        request_id,
                    )
                    raise ClassificationError(
                        "Failed to classify the query."
                    ) from exc

                resolved_handler = self.router.resolve_target(
                    classification,
                )

                logger.info(
                    "[%s] Classification-only request completed: "
                    "category=%s, handler=%s, latency_ms=%.1f, "
                    "elapsed_ms=%.1f",
                    request_id,
                    classification.category,
                    resolved_handler,
                    class_latency_ms,
                    (time.perf_counter() - start_time) * 1000.0,
                )

                return ClassificationResponse(
                    request_id=request_id,
                    category=str(classification.category),
                    urgency=str(classification.urgency),
                    complexity=str(classification.complexity),
                    confidence=classification.confidence,
                    target_agent=resolved_handler,
                    reason=classification.reason,
                    requires_clarification=(
                        classification.requires_clarification
                    ),
                    classification_latency_ms=round(
                        class_latency_ms,
                        2,
                    ),
                    status="success",
                )

        except (ClassificationError, ProviderTimeoutError):
            raise
        except Exception:
            logger.exception(
                "[%s] Unexpected classification processing failure.",
                request_id,
            )
            raise