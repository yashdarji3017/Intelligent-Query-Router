from typing import Optional, Protocol, runtime_checkable

from app.constants.prompts import CLASSIFIER_SYSTEM_PROMPT
from app.core.config import (
    Settings,
    get_gemini_model_name,
    get_google_api_key,
    get_settings,
)
from app.core.logger import get_logger
from app.schemas.classification import QueryClassification

logger = get_logger(__name__)


@runtime_checkable
class ClassifierAgentProtocol(Protocol):
    """Define the interface required for a query classification agent."""

    async def classify(self, query: str) -> QueryClassification:
        """
        Classify a natural-language query.

        Args:
            query: User query to classify.

        Returns:
            QueryClassification: Structured classification result.
        """
        ...


def clean_gemini_model_name(model_name: str) -> str:
    """
    Remove provider prefixes from a Gemini model identifier.

    Supports model names prefixed with ``google:`` or
    ``google-cloud:`` so the underlying Google model name can be used
    directly with the provider API.

    Args:
        model_name: Original Gemini model identifier.

    Returns:
        str: Model name without recognized provider prefixes.
    """
    return model_name.replace("google:", "").replace("google-cloud:", "")


class ClassifierAgent:
    """Classify user queries using a Google Gemini model."""

    def __init__(
        self,
        model_name: Optional[str] = None,
        settings: Optional[Settings] = None,
        custom_agent: Optional[object] = None,
    ) -> None:
        """
        Initialize the classifier with configuration or a custom agent.

        Uses the supplied settings or application defaults. A custom agent
        can be injected for testing or alternative classification backends.

        Args:
            model_name: Optional Gemini model name override.
            settings: Optional application settings instance.
            custom_agent: Optional preconfigured agent implementing
                an asynchronous ``run`` method.
        """
        self._settings = settings or get_settings()
        self._model_name = model_name or self._settings.gemini_model
        self._agent = custom_agent

        if self._agent is None:
            self._init_gemini_agent()

    def _init_gemini_agent(self) -> None:
        """
        Initialize the Pydantic AI agent with Google Gemini.

        Prefers the explicit Google provider API and falls back to the
        string-based model format when provider imports are unavailable.
        Initialization failures are logged and leave the agent unset so
        initialization can be retried when classification is requested.
        """
        try:
            from pydantic_ai import Agent

            api_key = (
                self._settings.google_api_key
                or get_google_api_key()
            )
            raw_model = (
                self._model_name
                or get_gemini_model_name()
            )
            clean_model = clean_gemini_model_name(raw_model)

            try:
                from pydantic_ai.models.google import GoogleModel
                from pydantic_ai.providers.google import GoogleProvider

                if api_key and str(api_key).strip():
                    provider = GoogleProvider(
                        api_key=str(api_key).strip(),
                    )
                    model = GoogleModel(
                        clean_model,
                        provider=provider,
                    )
                else:
                    model = GoogleModel(clean_model)

                self._agent = Agent(
                    model,
                    system_prompt=CLASSIFIER_SYSTEM_PROMPT,
                    output_type=QueryClassification,
                )

                logger.info(
                    "Initialized classifier agent with Google Gemini: "
                    "model=%s",
                    clean_model,
                )

            except (ImportError, AttributeError):
                target_model = f"google:{clean_model}"

                self._agent = Agent(
                    target_model,
                    system_prompt=CLASSIFIER_SYSTEM_PROMPT,
                    output_type=QueryClassification,
                )

                logger.info(
                    "Initialized classifier agent using model identifier: "
                    "%s",
                    target_model,
                )

        except ImportError:
            logger.warning(
                "Pydantic AI is not installed; classifier initialization "
                "is unavailable."
            )
            self._agent = None

        except Exception as exc:
            logger.exception(
                "Failed to initialize Google Gemini classifier agent: %s",
                exc,
            )
            self._agent = None

    async def classify(self, query: str) -> QueryClassification:
        """
        Classify a query and return a validated structured result.

        Initializes the Gemini agent on demand if necessary, executes the
        classification request, and normalizes supported response formats
        into the QueryClassification schema.

        Args:
            query: Non-empty natural-language query to classify.

        Returns:
            QueryClassification: Validated classification output.

        Raises:
            ValueError: If the query is empty or the model returns an
                unsupported response format.
            RuntimeError: If the Gemini agent cannot be initialized.
            Exception: Propagates model execution or validation errors.
        """
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query must be a non-empty string.")

        try:
            if self._agent is None:
                self._init_gemini_agent()

                if self._agent is None:
                    raise RuntimeError(
                        "Google Gemini Pydantic AI agent is not initialized."
                    )

            result = await self._agent.run(query)

            extracted = getattr(
                result,
                "output",
                getattr(result, "data", result),
            )

            if isinstance(extracted, QueryClassification):
                return extracted

            if isinstance(extracted, dict):
                return QueryClassification(**extracted)

            raise ValueError(
                "Classifier returned an unsupported response format: "
                f"{type(extracted).__name__}"
            )

        except (ValueError, RuntimeError):
            raise

        except Exception as exc:
            logger.exception(
                "Query classification failed: model=%s, error=%s",
                self._model_name,
                exc,
            )
            raise


_classifier_instance: Optional[ClassifierAgent] = None


def get_classifier_agent(
    settings: Optional[Settings] = None,
) -> ClassifierAgent:
    """
    Return the shared classifier agent instance.

    Creates the singleton lazily using the supplied settings on its first
    invocation. Subsequent calls reuse the existing instance.

    Args:
        settings: Optional settings used when creating the instance.

    Returns:
        ClassifierAgent: Shared classifier agent.
    """
    global _classifier_instance

    if _classifier_instance is None:
        _classifier_instance = ClassifierAgent(settings=settings)
        logger.debug("Created shared classifier agent instance.")

    return _classifier_instance


def set_classifier_agent(agent: ClassifierAgent) -> None:
    """
    Replace the shared classifier agent instance.

    Useful for dependency injection, testing, and swapping classifier
    implementations at runtime.

    Args:
        agent: Classifier agent instance to register.
    """
    global _classifier_instance

    _classifier_instance = agent
    logger.info("Shared classifier agent instance updated.")