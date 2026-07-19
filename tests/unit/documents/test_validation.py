from __future__ import annotations

from pathlib import Path

import pytest

from groundnote.config import Settings
from groundnote.documents import (
    detect_file_type,
    generate_safe_stored_filename,
    safe_display_filename,
    validate_local_file,
)
from groundnote.documents.errors import UnsafeFileError, UnsupportedFileTypeError
from groundnote.domain import SupportedFileType


def test_detect_file_type_allows_supported_extensions_case_insensitively() -> None:
    assert detect_file_type("NOTES.PDF") is SupportedFileType.PDF
    assert detect_file_type("notes.docx") is SupportedFileType.DOCX
    assert detect_file_type("notes.txt") is SupportedFileType.TXT
    assert detect_file_type("notes.markdown") is SupportedFileType.MARKDOWN


def test_detect_file_type_rejects_unsupported_extension() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        detect_file_type("notes.exe")


def test_safe_filename_rejects_empty_and_traversal() -> None:
    assert safe_display_filename("C:/private/notes.pdf") == "notes.pdf"
    with pytest.raises(UnsafeFileError):
        safe_display_filename("")
    with pytest.raises(UnsafeFileError):
        safe_display_filename("../notes.pdf")


def test_generate_safe_stored_filename_preserves_extension_and_uses_uuid() -> None:
    stored = generate_safe_stored_filename("Türkçe Notlar.PDF")

    assert stored.endswith(".pdf")
    assert ".." not in stored
    assert "/" not in stored
    assert "\\" not in stored


def test_validate_local_file_accepts_allowed_text_file(tmp_path: Path) -> None:
    path = tmp_path / "notes.txt"
    path.write_text("hello", encoding="utf-8")
    settings = Settings(data_directory=tmp_path / "app", maximum_upload_size_mb=1)

    result = validate_local_file(
        path,
        original_filename="NOTES.TXT",
        allowed_directory=tmp_path,
        settings=settings,
    )

    assert result.is_valid
    assert result.detected_file_type is SupportedFileType.TXT


def test_validate_local_file_rejects_unsafe_and_oversized_files(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.txt"
    outside.write_text("hello", encoding="utf-8")
    large = tmp_path / "large.txt"
    large.write_bytes(b"a" * ((1024 * 1024) + 1))
    settings = Settings(data_directory=tmp_path / "app", maximum_upload_size_mb=1)

    outside_result = validate_local_file(
        outside,
        original_filename="outside.txt",
        allowed_directory=tmp_path,
        settings=settings,
    )
    large_result = validate_local_file(
        large,
        original_filename="large.txt",
        allowed_directory=tmp_path,
        settings=Settings(data_directory=tmp_path / "app2", maximum_upload_size_mb=1),
    )

    assert not outside_result.is_valid
    assert outside_result.error_code == "unsafe_file"
    assert not large_result.is_valid
    assert large_result.error_code == "file_too_large"


def test_validate_local_file_rejects_binary_text_and_mismatched_pdf(tmp_path: Path) -> None:
    binary = tmp_path / "binary.txt"
    fake_pdf = tmp_path / "fake.pdf"
    binary.write_bytes(b"\x00\x01\x02\x03" * 100)
    fake_pdf.write_text("not a pdf", encoding="utf-8")
    settings = Settings(data_directory=tmp_path / "app")

    binary_result = validate_local_file(
        binary,
        original_filename="binary.txt",
        allowed_directory=tmp_path,
        settings=settings,
    )
    pdf_result = validate_local_file(
        fake_pdf,
        original_filename="fake.pdf",
        allowed_directory=tmp_path,
        settings=settings,
    )

    assert binary_result.error_code == "unsafe_file"
    assert pdf_result.error_code == "unsupported_file_type"
