"""Privacy-aware structured logging helpers."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, cast

import structlog

SENSITIVE_FIELD_NAMES = {
    "answer",
    "content",
    "document_text",
    "embedding",
    "embeddings",
    "file_path",
    "password",
    "prompt",
    "question",
    "secret",
    "token",
    "user_question",
}


def configure_logging(settings: Any) -> None:
    """Configure readable local structured logging explicitly."""
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, str(settings.log_level).upper()),
        stream=sys.stdout,
        force=True,
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _sanitize_event,
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, str(settings.log_level).upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.typing.FilteringBoundLogger:
    """Return a named structured logger."""
    return cast(structlog.typing.FilteringBoundLogger, structlog.get_logger(name))


def safe_filename(path: str | Path | None) -> str | None:
    """Return only a filename, never a full local path."""
    if path is None:
        return None
    return Path(path).name


def sanitize_log_fields(fields: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive values before they reach logs."""
    sanitized: dict[str, Any] = {}
    for key, value in fields.items():
        if key.lower() in SENSITIVE_FIELD_NAMES:
            sanitized[key] = "[redacted]"
        elif isinstance(value, Path):
            sanitized[key] = safe_filename(value)
        else:
            sanitized[key] = value
    return sanitized


def _sanitize_event(
    logger: Any,
    method_name: str,
    event_dict: structlog.typing.EventDict,
) -> structlog.typing.EventDict:
    return sanitize_log_fields(dict(event_dict))
