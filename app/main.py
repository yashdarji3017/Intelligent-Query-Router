import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import get_settings
from app.core.exceptions import AppBaseException
from app.core.logger import get_logger, setup_logging

logger = get_logger(__name__)


def _get_request_id(request: Request) -> str:
    """
    Retrieve the request ID or generate one when unavailable.

    Args:
        request: Incoming FastAPI request.

    Returns:
        str: Request identifier used for logging and error responses.
    """
    request_id = getattr(request.state, "request_id", None)

    if not request_id:
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id

    return request_id


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Manage application startup and shutdown operations.

    Loads application settings, configures logging, and records startup
    metadata. Logs a shutdown message when the application stops.

    Args:
        app: FastAPI application instance.
    """
    settings = get_settings()
    setup_logging(settings.log_level)

    logger.info(
        "Application starting: app_name=%s, environment=%s, "
        "model=%s, max_concurrency=%d",
        settings.app_name,
        settings.app_env,
        settings.gemini_model,
        settings.max_concurrent_requests,
    )

    try:
        yield
    finally:
        logger.info("Application shutting down.")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Registers API routes, application-specific exception handlers,
    request-validation handling, a generic server-error handler, and
    the root endpoint.

    Returns:
        FastAPI: Configured application instance.
    """
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=(
            "Stateless Intelligent Query Classification and Agent "
            "Routing System"
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(router)

    @app.exception_handler(AppBaseException)
    async def app_exception_handler(
        request: Request,
        exc: AppBaseException,
    ) -> JSONResponse:
        """
        Convert application-specific exceptions into structured responses.

        Args:
            request: Incoming request associated with the exception.
            exc: Application exception containing status and error metadata.

        Returns:
            JSONResponse: Standardized error response.
        """
        request_id = _get_request_id(request)

        logger.error(
            "[%s] Application error: type=%s, status_code=%d",
            request_id,
            exc.error_type,
            exc.status_code,
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "request_id": request_id,
                "status": "error",
                "error": exc.message,
                "error_type": exc.error_type,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        """
        Return a structured response for invalid request data.

        Logs validation locations and error types without logging submitted
        input values, which may contain sensitive information.

        Args:
            request: Incoming request that failed validation.
            exc: FastAPI request validation exception.

        Returns:
            JSONResponse: HTTP 422 validation error response.
        """
        request_id = _get_request_id(request)

        validation_summary = [
            {
                "location": error.get("loc"),
                "type": error.get("type"),
            }
            for error in exc.errors()
        ]

        logger.warning(
            "[%s] Request validation failed: errors=%s",
            request_id,
            validation_summary,
        )

        return JSONResponse(
            status_code=422,
            content={
                "request_id": request_id,
                "status": "error",
                "error": "Request validation failed.",
                "error_type": "ValidationError",
                "details": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """
        Handle unexpected server exceptions without exposing internals.

        Args:
            request: Incoming request associated with the failure.
            exc: Unexpected exception raised during request processing.

        Returns:
            JSONResponse: Generic HTTP 500 error response.
        """
        request_id = _get_request_id(request)

        logger.exception(
            "[%s] Unhandled server error: error_type=%s",
            request_id,
            type(exc).__name__,
        )

        return JSONResponse(
            status_code=500,
            content={
                "request_id": request_id,
                "status": "error",
                "error": (
                    "An internal server error occurred. "
                    "Please try again later."
                ),
                "error_type": "InternalServerError",
            },
        )

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        """
        Return basic service information and useful endpoint paths.

        Returns:
            dict[str, str]: Service message, API documentation path,
                and health-check path.
        """
        return {
            "message": (
                "Intelligent Query Classification and Agent Routing "
                "System is running."
            ),
            "docs": "/docs",
            "health": "/health",
        }

    logger.debug("FastAPI application configured successfully.")
    return app


app = create_app()