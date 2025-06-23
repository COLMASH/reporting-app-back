"""
Logging configuration using structlog.
"""

import logging
import sys
from enum import Enum
from typing import Any

import structlog
from structlog.processors import JSONRenderer, TimeStamper, add_log_level

from src.config import settings


class LogLevels(str, Enum):
    """Log level enumeration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def configure_logging(level: str | None = None) -> None:
    """
    Configure structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    log_level = level or settings.log_level

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s", stream=sys.stdout, level=getattr(logging, log_level.upper())
    )

    # Configure structlog
    processors: list[Any] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    # Use JSON renderer in production, console renderer in development
    if settings.is_production:
        processors.extend([structlog.processors.format_exc_info, JSONRenderer()])
    else:
        # ConsoleRenderer handles exceptions internally, so we don't need format_exc_info
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return structlog.get_logger(name)


# Configure logging on import
configure_logging()
