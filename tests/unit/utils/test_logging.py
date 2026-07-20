from __future__ import annotations

import logging
from pathlib import Path

import pytest

from groundnote.config import Settings
from groundnote.ui.errors import safe_failure_message
from groundnote.ui.state import (
    ACTIVE_OPERATION,
    OperationStatus,
    begin_operation,
    end_operation,
    initialize_session_state,
)
from groundnote.utils import (
    configure_logging,
    get_logger,
    safe_filename,
    safe_log_info,
    sanitize_log_fields,
)
from groundnote.utils.logging import HANDLER_MARKER


class BrokenLogger:
    def warning(self, event: str, **fields: object) -> None:
        raise OSError(22, "Invalid argument")


class BrokenInfoLogger:
    def info(self, event: str, **fields: object) -> None:
        raise OSError(22, "Invalid argument")


def test_safe_filename_removes_parent_path() -> None:
    assert safe_filename(Path("private") / "notes.pdf") == "notes.pdf"


def test_sanitize_log_fields_redacts_sensitive_content() -> None:
    result = sanitize_log_fields(
        {
            "question": "full private question",
            "embedding": [1.0, 2.0],
            "api_key": "redaction input",
            "authorization": "redaction header",
            "file_path": Path("private") / "notes.pdf",
            "operation_id": "op-1",
            "metadata": {
                "prompt": "private nested prompt",
                "content": "private nested content",
                "safe_path": Path("private") / "nested.pdf",
            },
            "events": [{"answer": "private nested answer"}],
        }
    )

    assert result["question"] == "[redacted]"
    assert result["embedding"] == "[redacted]"
    assert result["api_key"] == "[redacted]"
    assert result["authorization"] == "[redacted]"
    assert result["file_path"] == "[redacted]"
    assert result["operation_id"] == "op-1"
    assert result["metadata"]["prompt"] == "[redacted]"
    assert result["metadata"]["content"] == "[redacted]"
    assert result["metadata"]["safe_path"] == "nested.pdf"
    assert result["events"] == [{"answer": "[redacted]"}]


@pytest.mark.parametrize("event", ["ui_document_operation_failed", "ui_question_failed"])
def test_broken_windows_stream_does_not_mask_original_safe_error(event: str) -> None:
    original = RuntimeError(r"private failure at C:\Users\private\document.pdf")

    message = safe_failure_message(original, logger=BrokenLogger(), event=event)

    assert message.title == "Operation failed"
    assert "Invalid argument" not in message.message
    assert "C:\\Users" not in message.message


def test_logging_failure_cannot_prevent_operation_finally_reset() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    operation = begin_operation(state, "question")

    try:
        safe_failure_message(
            RuntimeError("original provider failure"),
            logger=BrokenLogger(),
            event="ui_question_failed",
        )
    finally:
        end_operation(state, operation, succeeded=False)

    completed = state[ACTIVE_OPERATION]
    assert completed.status is OperationStatus.FAILED
    assert completed.active is False


def test_safe_info_logging_swallows_invalid_windows_handle() -> None:
    safe_log_info(BrokenInfoLogger(), "event", error_type="RuntimeError")


def test_logging_reconfiguration_is_idempotent_and_privacy_safe(tmp_path: Path) -> None:
    settings = Settings(data_directory=tmp_path / "app")
    settings.initialize_directories()

    configure_logging(settings)
    configure_logging(settings)
    managed = [
        handler
        for handler in logging.getLogger("groundnote").handlers
        if bool(getattr(handler, HANDLER_MARKER, False))
    ]
    logger = get_logger("groundnote.test")
    private_path = tmp_path / "private" / "notes.pdf"
    safe_log_info(
        logger,
        "privacy_test",
        file_path=private_path,
        question="complete private query",
    )
    for handler in managed:
        handler.flush()

    assert len(managed) == 1
    assert settings.log_directory is not None
    log_text = (settings.log_directory / "groundnote.log").read_text(encoding="utf-8")
    assert str(tmp_path) not in log_text
    assert "complete private query" not in log_text
    assert "[redacted]" in log_text

    moved_log = settings.log_directory / "groundnote.moved.log"
    (settings.log_directory / "groundnote.log").replace(moved_log)
    moved_log.replace(settings.log_directory / "groundnote.log")
