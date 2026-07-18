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
