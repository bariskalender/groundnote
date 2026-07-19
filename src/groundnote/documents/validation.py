"""Secure local file validation and safe filename handling."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from uuid import uuid4

from groundnote.config import Settings
from groundnote.documents.errors import (
    EmptyDocumentError,
    FileTooLargeError,
    UnsafeFileError,
    UnsupportedFileTypeError,
)
from groundnote.documents.models import ValidationResult
from groundnote.domain import SupportedFileType

ALLOWED_EXTENSIONS: dict[str, SupportedFileType] = {
    ".pdf": SupportedFileType.PDF,
    ".docx": SupportedFileType.DOCX,
    ".txt": SupportedFileType.TXT,
    ".md": SupportedFileType.MARKDOWN,
    ".markdown": SupportedFileType.MARKDOWN,
}
PDF_SIGNATURE = b"%PDF-"
ZIP_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._ -]+", re.UNICODE)


def detect_file_type(filename: str) -> SupportedFileType:
    suffix = Path(filename).suffix.lower()
    try:
        return ALLOWED_EXTENSIONS[suffix]
    except KeyError as exc:
        raise UnsupportedFileTypeError() from exc


def generate_safe_stored_filename(original_filename: str) -> str:
    """Create a traversal-safe, collision-resistant stored filename."""
    safe_original = safe_display_filename(original_filename)
    stem = Path(safe_original).stem
    suffix = Path(safe_original).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError()
    normalized_stem = unicodedata.normalize("NFKC", stem)
    normalized_stem = _SAFE_FILENAME_RE.sub("_", normalized_stem).strip(" ._")
    if not normalized_stem:
        normalized_stem = "document"
    return f"{uuid4().hex}_{normalized_stem}{suffix}"


def safe_display_filename(filename: str) -> str:
    """Return only a filename, rejecting traversal and empty names."""
    normalized = filename.replace("\\", "/")
    if ".." in normalized.split("/"):
        raise UnsafeFileError("The filename is not safe.")
    cleaned = normalized.split("/")[-1].strip()
    if not cleaned or cleaned in {".", ".."}:
        raise UnsafeFileError("The filename is not safe.")
    return cleaned


def validate_local_file(
    file_path: Path,
    *,
    original_filename: str,
    allowed_directory: Path,
    settings: Settings,
) -> ValidationResult:
    """Validate a local file before hashing or parsing."""
    warnings: list[str] = []
    try:
        safe_display_filename(original_filename)
        file_type = detect_file_type(original_filename)
        resolved_file = file_path.resolve(strict=True)
        resolved_allowed = allowed_directory.resolve(strict=True)
        if resolved_file == resolved_allowed or resolved_allowed not in resolved_file.parents:
            raise UnsafeFileError("The file is outside the allowed document directory.")
        if not resolved_file.is_file():
            raise UnsafeFileError("The selected path is not a regular file.")
        size = resolved_file.stat().st_size
        if size == 0:
            raise EmptyDocumentError()
        max_bytes = settings.maximum_upload_size_mb * 1024 * 1024
        if size > max_bytes:
            raise FileTooLargeError()
        _validate_content_signature(resolved_file, file_type)
        return ValidationResult(
            is_valid=True,
            detected_file_type=file_type,
            size_bytes=size,
            warnings=warnings,
        )
    except (
        EmptyDocumentError,
        FileTooLargeError,
        UnsafeFileError,
        UnsupportedFileTypeError,
    ) as exc:
        size = file_path.stat().st_size if file_path.exists() and file_path.is_file() else 0
        return ValidationResult(
            is_valid=False,
            size_bytes=size,
            warnings=warnings,
            error_code=exc.error_code,
            user_message=str(exc),
        )


def is_binary_looking(data: bytes) -> bool:
    """Return true when bytes are unlikely to be human-readable text."""
    if not data:
        return False
    null_count = data.count(b"\x00")
    if null_count > max(1, len(data) // 100):
        return True
    control = sum(1 for byte in data if byte < 32 and byte not in {9, 10, 12, 13})
    return control / len(data) > 0.30


def _validate_content_signature(file_path: Path, file_type: SupportedFileType) -> None:
    with file_path.open("rb") as file:
        head = file.read(4096)
    if file_type is SupportedFileType.PDF and not head.startswith(PDF_SIGNATURE):
        raise UnsupportedFileTypeError("The file extension and PDF signature do not match.")
    if file_type is SupportedFileType.DOCX and not head.startswith(ZIP_SIGNATURES):
        raise UnsupportedFileTypeError("The file extension and DOCX container do not match.")
    if file_type in {SupportedFileType.TXT, SupportedFileType.MARKDOWN} and is_binary_looking(head):
        raise UnsafeFileError("The text file appears to contain binary data.")
