"""Shared parser helpers."""

from __future__ import annotations

from groundnote.documents.errors import NoExtractableTextError
from groundnote.documents.models import ParsedSection
from groundnote.documents.normalization import normalize_text


def make_section(
    text: str,
    *,
    source_order: int,
    page_number: int | None = None,
    section_title: str | None = None,
    warnings: list[str] | None = None,
) -> ParsedSection | None:
    normalized = normalize_text(text)
    if not normalized:
        return None
    return ParsedSection(
        text=normalized,
        page_number=page_number,
        section_title=section_title,
        source_order=source_order,
        warnings=warnings or [],
    )


def require_sections(sections: list[ParsedSection], *, scanned_hint: bool = False) -> None:
    if sections:
        return
    if scanned_hint:
        raise NoExtractableTextError(
            "No readable text could be extracted. The document may be scanned; OCR is not "
            "supported in this version."
        )
    raise NoExtractableTextError()
