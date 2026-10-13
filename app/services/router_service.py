from typing import Awaitable, Callable, Dict, Optional

from app.agents.handlers import (
    account_handler,
    billing_handler,
    complex_handler,
    fallback_handler,
    general_handler,
    technical_handler,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import HandlerExecutionError, RoutingError
from app.core.logger import get_logger
from app.schemas.classification import QueryClassification

logger = get_logger(__name__)

HandlerFunc = Callable[[str, QueryClassification], Awaitable[str]]


DEFAULT_HANDLERS: Dict[str, HandlerFunc] = {
    "general_handler": general_handler,
    "technical_handler": technical_handler,
    "account_handler": account_handler,
    "billing_handler": billing_handler,
    "complex_handler": complex_handler,
    "fallback_handler": fallback_handler,
}


class HandlerRegistry:
    """Manage the available asynchronous query handlers."""

    def __init__(
        self,
        handlers: Optional[Dict[str, HandlerFunc]] = None,
    ) -> None:
        """
        Initialize the registry with the supplied handlers or defaults.

        Args:
            handlers: Optional mapping of handler names to asynchronous
                handler functions. Defaults to the built-in handlers.
        """
        self._handlers: Dict[str, HandlerFunc] = dict(
            DEFAULT_HANDLERS if handlers is None else handlers
        )

    def get_handler(self, name: str) -> Optional[HandlerFunc]:
        """
        Retrieve a registered handler by name.

        Args:
            name: Registered handler identifier.

        Returns:
            Optional[HandlerFunc]: Handler function when found; otherwise None.
        """
        return self._handlers.get(name)

    def register(
        self,
        name: str,
        handler: HandlerFunc,
    ) -> None:
        """
        Register or replace an asynchronous query handler.

        Args:
            name: Non-empty identifier for the handler.
            handler: Asynchronous function that processes a query and its
                classification.

        Raises:
            ValueError: If the handler name is empty or the handler is not
                callable.
        """
        if not name or not name.strip():
            raise ValueError("Handler name must not be empty.")

        if not callable(handler):
            raise ValueError("Handler must be callable.")

        self._handlers[name.strip()] = handler

        logger.info(
            "Registered query handler: name=%s",
            name.strip(),
        )


class DeterministicRouter:
    """
    Resolve classified queries to handlers using explicit routing rules.

    Routes queries by category, confidence threshold, and clarification
    requirements. Executes the selected asynchronous handler through the
    handler registry.
    """

    CATEGORY_ROUTING_MAP: Dict[str, str] = {
        "general": "general_handler",
        "technical": "technical_handler",
        "account": "account_handler",
        "billing": "billing_handler",
        "complex": "complex_handler",
        "unknown": "fallback_handler",
    }

    FALLBACK_HANDLER: str = "fallback_handler"

    def __init__(
        self,
        registry: Optional[HandlerRegistry] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        """
        Initialize the router and its dependencies.

        Args:
            registry: Optional registry containing available handlers.
            settings: Optional application settings used for confidence
                threshold evaluation.
        """
        self.registry = registry or HandlerRegistry()
        self.settings = settings or get_settings()

    def resolve_target(
        self,
        classification: QueryClassification,
    ) -> str:
        """
        Determine the appropriate handler for a classification result.

        Routes queries requiring clarification or having confidence below
        the configured threshold to the fallback handler. Other queries
        are routed according to their classified category.

        Args:
            classification: Validated classification result for the query.

        Returns:
            str: Name of the selected handler.

        Raises:
            RoutingError: If the classification cannot be evaluated.
        """
        try:
            if classification.requires_clarification:
                logger.info(
                    "Query requires clarification: category=%s, "
                    "confidence=%.2f; routing to fallback.",
                    classification.category,
                    classification.confidence,
                )
                return self.FALLBACK_HANDLER

            threshold = (
                self.settings.classification_confidence_threshold
            )

            if classification.confidence < threshold:
                logger.info(
                    "Classification confidence below threshold: "
                    "confidence=%.2f, threshold=%.2f; routing to fallback.",
                    classification.confidence,
                    threshold,
                )
                return self.FALLBACK_HANDLER

            category_key = str(classification.category).lower()

            # Support both plain strings and string-backed enum values.
            if "." in category_key:
                category_key = category_key.rsplit(".", 1)[-1]

            target_handler = self.CATEGORY_ROUTING_MAP.get(
                category_key,
                self.FALLBACK_HANDLER,
            )

            logger.debug(
                "Resolved query category to handler: category=%s, "
                "handler=%s",
                category_key,
                target_handler,
            )

            return target_handler

        except Exception as exc:
            logger.exception("Failed to resolve query routing target.")

            raise RoutingError(
                "Unable to resolve an appropriate query handler."
            ) from exc

    async def dispatch(
        self,
        handler_name: str,
        query: str,
        classification: QueryClassification,
    ) -> str:
        """
        Execute the selected asynchronous query handler.

        Looks up the handler in the registry, invokes it with the original
        query and classification, and validates that it returns a string.

        Args:
            handler_name: Name of the registered handler to execute.
            query: Original user query.
            classification: Classification result passed to the handler.

        Returns:
            str: Response generated by the selected handler.

        Raises:
            RoutingError: If the requested handler is not registered.
            HandlerExecutionError: If handler execution fails or returns
                an unsupported result.
        """
        handler_func = self.registry.get_handler(handler_name)

        if handler_func is None:
            logger.error(
                "Requested handler is not registered: handler=%s",
                handler_name,
            )
            raise RoutingError(
                f"Handler '{handler_name}' is not registered or supported."
            )

        try:
            response = await handler_func(query, classification)

            if not isinstance(response, str):
                raise TypeError(
                    "Handler must return a string response."
                )

            logger.debug(
                "Handler executed successfully: handler=%s, "
                "response_length=%d",
                handler_name,
                len(response),
            )

            return response

        except Exception as exc:
            logger.exception(
                "Handler execution failed: handler=%s",
                handler_name,
            )

            raise HandlerExecutionError(
                f"Handler '{handler_name}' failed to process the request."
            ) from exc