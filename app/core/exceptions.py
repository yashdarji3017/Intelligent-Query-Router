from typing import Optional


class AppBaseException(Exception):
    """Base exception for application-specific errors."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_type: Optional[str] = None,
    ) -> None:
        """
        Initialize a standardized application exception.

        Args:
            message: Human-readable description of the error.
            status_code: HTTP status code associated with the exception.
            error_type: Optional error identifier; defaults to the class name.
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_type = error_type or self.__class__.__name__


class ProviderError(AppBaseException):
    """Represent an error returned by or encountered with an LLM provider."""

    def __init__(
        self,
        message: str = "LLM provider error occurred",
    ) -> None:
        """
        Initialize an LLM provider exception.

        Args:
            message: Description of the provider failure.
        """
        super().__init__(
            message,
            status_code=502,
            error_type="ProviderError",
        )


class ProviderTimeoutError(ProviderError):
    """Represent a timeout while waiting for an LLM provider response."""

    def __init__(
        self,
        message: str = "LLM provider request timed out",
    ) -> None:
        """
        Initialize a provider timeout exception.

        Args:
            message: Description of the timeout failure.
        """
        super().__init__(message)
        self.status_code = 504
        self.error_type = "ProviderTimeoutError"


class RateLimitError(ProviderError):
    """Represent an LLM provider rate-limit rejection."""

    def __init__(
        self,
        message: str = (
            "Provider rate limit exceeded. Please retry later."
        ),
    ) -> None:
        """
        Initialize a provider rate-limit exception.

        Args:
            message: Description of the rate-limit condition.
        """
        super().__init__(message)
        self.status_code = 429
        self.error_type = "RateLimitError"


class ClassificationError(AppBaseException):
    """Represent a query classification or output validation failure."""

    def __init__(
        self,
        message: str = "Failed to classify query",
    ) -> None:
        """
        Initialize a query classification exception.

        Args:
            message: Description of the classification failure.
        """
        super().__init__(
            message,
            status_code=422,
            error_type="ClassificationError",
        )


class RoutingError(AppBaseException):
    """Represent a failure to resolve an appropriate query handler."""

    def __init__(
        self,
        message: str = "Routing resolution failed",
    ) -> None:
        """
        Initialize a query routing exception.

        Args:
            message: Description of the routing failure.
        """
        super().__init__(
            message,
            status_code=500,
            error_type="RoutingError",
        )


class HandlerExecutionError(AppBaseException):
    """Represent a failure while executing a query handler."""

    def __init__(
        self,
        message: str = "Handler failed to process request",
    ) -> None:
        """
        Initialize a handler execution exception.

        Args:
            message: Description of the handler failure.
        """
        super().__init__(
            message,
            status_code=500,
            error_type="HandlerExecutionError",
        )