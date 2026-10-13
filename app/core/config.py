import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.logger import get_logger

logger = get_logger(__name__)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    logger.debug(
        "python-dotenv is not installed; relying on environment variables."
    )


class Settings(BaseSettings):
    """
    Define validated application configuration.

    Loads configuration from environment variables and the optional .env file.
    Pydantic validates configured values and applies defaults when optional
    settings are not provided.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Intelligent Query Classification and Routing System"
    app_env: str = Field(
        default="development",
        alias="APP_ENV",
    )
    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
    )

    google_api_key: Optional[str] = Field(
        default=None,
        alias="GOOGLE_API_KEY",
    )
    gemini_model: str = Field(
        default="gemini-3.6-flash",
        alias="GEMINI_MODEL",
    )

    classification_confidence_threshold: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
        alias="CLASSIFICATION_CONFIDENCE_THRESHOLD",
    )
    max_concurrent_requests: int = Field(
        default=6,
        ge=1,
        alias="MAX_CONCURRENT_REQUESTS",
    )
    request_timeout_seconds: float = Field(
        default=30.0,
        gt=0.0,
        alias="REQUEST_TIMEOUT_SECONDS",
    )
    max_retries: int = Field(
        default=2,
        ge=0,
        alias="MAX_RETRIES",
    )
    retry_backoff_base_seconds: float = Field(
        default=0.5,
        ge=0.0,
        alias="RETRY_BACKOFF_BASE_SECONDS",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the cached application settings instance.

    Caches the validated configuration so repeated dependency calls reuse
    the same instance rather than reparsing environment configuration.

    Returns:
        Settings: Validated application configuration.
    """
    try:
        settings = Settings()
        logger.debug(
            "Application settings loaded: environment=%s, model=%s",
            settings.app_env,
            settings.gemini_model,
        )
        return settings
    except Exception:
        logger.exception("Failed to load application settings.")
        raise


def get_google_api_key() -> Optional[str]:
    """
    Retrieve the configured Google API key.

    Prefers the validated settings value and falls back to the environment
    variable when the settings value is empty.

    Returns:
        Optional[str]: Google API key, or None when not configured.
    """
    try:
        api_key = (
            get_settings().google_api_key
            or os.getenv("GOOGLE_API_KEY")
        )

        if not api_key or not api_key.strip():
            logger.debug("Google API key is not configured.")
            return None

        return api_key.strip()
    except Exception:
        logger.exception("Failed to retrieve Google API key configuration.")
        raise


def get_gemini_model_name() -> str:
    """
    Retrieve the configured Gemini model name.

    Uses the validated application settings and falls back to the
    environment variable or the default model identifier.

    Returns:
        str: Gemini model name.
    """
    try:
        model_name = (
            get_settings().gemini_model
            or os.getenv("GEMINI_MODEL")
            or "gemini-3.6-flash"
        ).strip()

        if not model_name:
            logger.warning(
                "Gemini model name is empty; using the default model."
            )
            return "gemini-3.6-flash"

        return model_name
    except Exception:
        logger.exception("Failed to retrieve Gemini model configuration.")
        raise