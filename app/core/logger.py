import logging
import os
import sys
from pathlib import Path
from typing import Optional

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_DIR = Path("/tmp/logs") if os.getenv("VERCEL") else Path("logs")
LOG_FILE = LOG_DIR / "app.log"

LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LOG_DIR.mkdir(parents=True, exist_ok=True)


def _get_numeric_level(log_level: str) -> int:
    """
    Resolve a logging level name to its numeric value.

    Args:
        log_level: Logging level name, such as DEBUG, INFO, or ERROR.

    Returns:
        int: Corresponding logging level, defaulting to INFO if invalid.
    """
    numeric_level = getattr(logging, log_level.upper(), None)

    if not isinstance(numeric_level, int):
        logging.getLogger(__name__).warning(
            "Invalid log level '%s'; falling back to INFO.",
            log_level,
        )
        return logging.INFO

    return numeric_level


def get_logger(name: str) -> logging.Logger:
    """
    Retrieve a configured application logger.

    Configures console and file handlers the first time a named logger is
    requested. Existing handlers are preserved to prevent duplicate log
    messages when the logger is requested repeatedly.

    Args:
        name: Name used to identify the logger.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(_get_numeric_level(LOG_LEVEL))
    logger.propagate = False

    formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=DATE_FORMAT,
    )

    try:
        file_handler = logging.FileHandler(
            LOG_FILE,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError as exc:
        # Continue with console logging if the file cannot be opened.
        logging.getLogger(__name__).warning(
            "File logging unavailable at %s: %s",
            LOG_FILE,
            exc,
        )

    console_stream = sys.stdout

    if hasattr(console_stream, "reconfigure"):
        try:
            console_stream.reconfigure(encoding="utf-8")
        except (OSError, ValueError):
            pass

    console_handler = logging.StreamHandler(console_stream)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def setup_logging(log_level: Optional[str] = None) -> logging.Logger:
    """
    Configure application-wide logging and return the main logger.

    Updates the root logger's level and applies the requested level to
    application loggers created through this module.

    Args:
        log_level: Optional logging level override. Uses the LOG_LEVEL
            environment variable or INFO when omitted.

    Returns:
        logging.Logger: Main application logger.
    """
    global LOG_LEVEL

    if log_level:
        LOG_LEVEL = log_level.upper()

    numeric_level = _get_numeric_level(LOG_LEVEL)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    app_logger = get_logger("app")
    app_logger.setLevel(numeric_level)

    for handler in app_logger.handlers:
        handler.setLevel(numeric_level)

    return app_logger


logger = get_logger("app")