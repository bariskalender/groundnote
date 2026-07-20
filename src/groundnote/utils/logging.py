"""Privacy-aware structured logging helpers."""

from __future__ import annotations

import logging
from contextlib import suppress
from pathlib import Path
from typing import Any, cast

import structlog

SENSITIVE_FIELD_NAMES = {
    "answer",
    "api_key",
    "authorization",
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


LOGGER_NAME = "groundnote"
LOG_FILENAME = "groundnote.log"
HANDLER_MARKER = "_groundnote_managed_handler"


class ClosingUtf8FileHandler(logging.Handler):
    """Write one local log record at a time without retaining a Windows file handle."""

    terminator = "\n"

    def __init__(self, path: Path, *, max_bytes: int, backup_count: int) -> None:
        super().__init__()
        self.path = path
        self.max_bytes = max_bytes
        self.backup_count = backup_count

    def emit(self, record: logging.LogRecord) -> None:
        try:
            rendered = f"{self.format(record)}{self.terminator}"
            encoded_size = len(rendered.encode())
            self._rotate_if_needed(encoded_size)
            with self.path.open("a", encoding="utf-8", errors="backslashreplace") as stream:
                stream.write(rendered)
                stream.flush()
        except Exception:
            self.handleError(record)

    def _rotate_if_needed(self, incoming_size: int) -> None:
        if self.max_bytes <= 0 or not self.path.exists():
            return
        if self.path.stat().st_size + incoming_size <= self.max_bytes:
            return
        for index in range(self.backup_count, 0, -1):
            source = (
                self.path if index == 1 else self.path.with_name(f"{self.path.name}.{index - 1}")
            )
            target = self.path.with_name(f"{self.path.name}.{index}")
            if source.exists():
                source.replace(target)


def configure_logging(settings: Any) -> None:
    """Configure idempotent UTF-8 file logging without caching Streamlit streams."""
    level = getattr(logging, str(settings.log_level).upper())
    logging.raiseExceptions = False
    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.dev.ConsoleRenderer(colors=False),
        foreign_pre_chain=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _sanitize_event,
        ],
    )
    handler = _build_handler(settings)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    setattr(handler, HANDLER_MARKER, True)

    standard_logger = logging.getLogger(LOGGER_NAME)
    for existing in list(standard_logger.handlers):
        if bool(getattr(existing, HANDLER_MARKER, False)):
            standard_logger.removeHandler(existing)
            with suppress(OSError, ValueError):
                existing.close()
    standard_logger.addHandler(handler)
    standard_logger.setLevel(level)
    standard_logger.propagate = False

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _sanitize_event,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a named structured logger."""
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))


def safe_log_info(logger: Any, event: str, **fields: Any) -> None:
    """Best-effort informational logging that cannot fail the caller."""
    _safe_log(logger, "info", event, fields)


def safe_log_warning(logger: Any, event: str, **fields: Any) -> None:
    """Best-effort warning logging for user-facing failure paths."""
    _safe_log(logger, "warning", event, fields)


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
            sanitized[key] = _sanitize_value(value)
    return sanitized


def _sanitize_event(
    logger: Any,
    method_name: str,
    event_dict: structlog.typing.EventDict,
) -> structlog.typing.EventDict:
    return sanitize_log_fields(dict(event_dict))


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return sanitize_log_fields(value)
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_value(item) for item in value)
    if isinstance(value, Path):
        return safe_filename(value)
    return value


def _build_handler(settings: Any) -> logging.Handler:
    log_directory = getattr(settings, "log_directory", None)
    if isinstance(log_directory, Path):
        try:
            return ClosingUtf8FileHandler(
                log_directory / LOG_FILENAME,
                max_bytes=2 * 1024 * 1024,
                backup_count=2,
            )
        except (OSError, ValueError):
            pass
    return logging.NullHandler()


def _safe_log(logger: Any, method_name: str, event: str, fields: dict[str, Any]) -> None:
    try:
        method = getattr(logger, method_name)
        method(event, **sanitize_log_fields(fields))
    except Exception:
        return
