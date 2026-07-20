"""Deterministic privacy-safe UI formatting helpers."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import PurePath

from groundnote.domain import DocumentStatus, SupportedFileType
from groundnote.rag import Citation
from groundnote.ui.models import CitationView

STATUS_LABELS: dict[DocumentStatus, str] = {
    DocumentStatus.PENDING: "Pending",
    DocumentStatus.PARSING: "Processing",
    DocumentStatus.PARSED: "Processed",
    DocumentStatus.PENDING_EMBEDDING: "Waiting for indexing",
    DocumentStatus.INDEXING: "Indexing",
    DocumentStatus.INDEXED: "Ready",
    DocumentStatus.FAILED: "Failed",
    DocumentStatus.INCOMPATIBLE_INDEX: "Index update required",
}

FILE_TYPE_LABELS: dict[SupportedFileType, str] = {
    SupportedFileType.PDF: "PDF",
    SupportedFileType.DOCX: "DOCX",
    SupportedFileType.TXT: "TXT",
    SupportedFileType.MARKDOWN: "Markdown",
}
STORED_FILENAME_PREFIX = re.compile(r"^[0-9a-fA-F]{32}_(?=.)")


def format_file_size(size_bytes: int | None) -> str:
    """Format bytes without depending on the host locale."""
    if size_bytes is None or size_bytes < 0:
        return "Not available"
    value = float(size_bytes)
    units = ("B", "KB", "MB", "GB")
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return "Not available"


def format_duration(duration_ms: float | None) -> str:
    """Format an operation duration using readable stable units."""
    if duration_ms is None or duration_ms < 0:
        return "Not available"
    if duration_ms < 1000:
        return f"{duration_ms:.0f} ms"
    return f"{duration_ms / 1000:.2f} s"


def format_timestamp(value: datetime | None) -> str:
    """Format timestamps in UTC for deterministic cross-platform display."""
    if value is None:
        return "Not available"
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def format_status(status: DocumentStatus | None) -> str:
    """Map internal status values to user-facing labels."""
    if status is None:
        return "Unknown"
    return STATUS_LABELS.get(status, "Unknown")


def format_file_type(file_type: SupportedFileType | None) -> str:
    """Map supported file types to compact display labels."""
    if file_type is None:
        return "Unknown"
    return FILE_TYPE_LABELS.get(file_type, "Unknown")


def safe_filename(filename: str | None, *, maximum_length: int = 64) -> str:
    """Return a path-free, visually bounded filename."""
    if not filename:
        return "document"
    normalized = filename.replace("\\", "/")
    name = PurePath(normalized).name.strip() or "document"
    name = STORED_FILENAME_PREFIX.sub("", name) or "document"
    if len(name) <= maximum_length:
        return name
    suffix = PurePath(name).suffix
    available = max(1, maximum_length - len(suffix) - 1)
    return f"{name[:available]}…{suffix}"


def format_warning(warning: str) -> str:
    """Convert a safe warning code into readable text."""
    cleaned = " ".join(warning.replace("_", " ").split()).strip()
    if not cleaned:
        return "A local processing warning was reported."
    return cleaned[0].upper() + cleaned[1:]


def citation_to_view(citation: Citation) -> CitationView:
    """Build display data from trusted structured citation metadata."""
    filename = safe_filename(citation.source_filename, maximum_length=80)
    section = _safe_section(citation.section_title)
    chunk_number = citation.chunk_index + 1
    if citation.source_file_type is SupportedFileType.PDF and citation.page_number is not None:
        label = f"{filename} — page {citation.page_number}"
    elif (
        citation.source_file_type
        in {
            SupportedFileType.DOCX,
            SupportedFileType.MARKDOWN,
        }
        and section
    ):
        label = f"{filename} — {section}"
    elif citation.source_file_type is SupportedFileType.TXT:
        label = f"{filename} — chunk {chunk_number}"
    else:
        label = filename
    return CitationView(
        citation_id=citation.citation_id,
        label=label,
        file_type=format_file_type(citation.source_file_type),
        page_number=citation.page_number,
        section_title=section,
        chunk_number=chunk_number,
        score=citation.score,
    )


def _safe_section(section: str | None) -> str | None:
    if section is None:
        return None
    cleaned = " ".join(section.replace("\\", " ").replace("/", " ").split())
    return cleaned[:120] or None
