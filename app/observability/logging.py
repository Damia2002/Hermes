"""Structured JSON logging with structlog."""

import logging
import sys
from pathlib import Path

import structlog

from app.config import get_settings

settings = get_settings()


def configure_logging() -> None:
    Path(settings.log_dir).mkdir(parents=True, exist_ok=True)
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        level=log_level,
        handlers=[logging.StreamHandler(sys.stdout)],
        format="%(message)s",
    )


def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)
