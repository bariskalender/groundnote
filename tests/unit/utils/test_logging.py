from __future__ import annotations

from pathlib import Path

from groundnote.utils import safe_filename, sanitize_log_fields


def test_safe_filename_removes_parent_path() -> None:
    assert safe_filename(Path("private") / "notes.pdf") == "notes.pdf"


def test_sanitize_log_fields_redacts_sensitive_content() -> None:
    result = sanitize_log_fields(
        {
            "question": "full private question",
            "embedding": [1.0, 2.0],
            "file_path": Path("private") / "notes.pdf",
            "operation_id": "op-1",
        }
    )

    assert result["question"] == "[redacted]"
    assert result["embedding"] == "[redacted]"
    assert result["file_path"] == "[redacted]"
    assert result["operation_id"] == "op-1"
