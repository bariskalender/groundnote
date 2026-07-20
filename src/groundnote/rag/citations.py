"""Trusted citation formatting and validation."""

from __future__ import annotations

import re
from pathlib import PurePath

from groundnote.domain import SupportedFileType
from groundnote.rag.errors import CitationValidationError
from groundnote.rag.models import Citation, RagContextItem

CITATION_RE = re.compile(r"\[(S[1-9]\d*)\]")


def citation_for_context(item: RagContextItem) -> Citation:
    """Build a trusted citation from retrieved metadata only."""
    filename = _safe_filename(item.source_filename)
    section = _safe_section(item.section_title)
    label = _display_label(
        filename=filename,
        file_type=item.source_file_type,
        page_number=item.page_number,
        section_title=section,
        chunk_index=item.chunk_index,
    )
    return Citation(
        citation_id=item.citation_id,
        document_id=item.document_id,
        chunk_id=item.chunk_id,
        source_filename=filename,
        source_file_type=item.source_file_type,
        page_number=item.page_number,
        section_title=section,
        chunk_index=item.chunk_index,
        display_label=label,
        score=item.score,
    )


def extract_citation_ids(answer: str, allowed_ids: set[str]) -> list[str]:
    """Extract allowed citation IDs in first-use order."""
    seen: set[str] = set()
    ordered: list[str] = []
    for citation_id in CITATION_RE.findall(answer):
        if citation_id not in allowed_ids or citation_id in seen:
            continue
        seen.add(citation_id)
        ordered.append(citation_id)
    return ordered


def strip_unknown_citations(answer: str, allowed_ids: set[str]) -> str:
    """Remove unsupported citation tokens without inventing trusted metadata."""
    return CITATION_RE.sub(
        lambda match: match.group(0) if match.group(1) in allowed_ids else "",
        answer,
    )


def validate_citation_map(items: list[RagContextItem]) -> dict[str, Citation]:
    """Return citation map and reject duplicate source IDs."""
    citations: dict[str, Citation] = {}
    for item in items:
        if item.citation_id in citations:
            raise CitationValidationError("Duplicate citation id in RAG context.")
        citations[item.citation_id] = citation_for_context(item)
    return citations


def _display_label(
    *,
    filename: str,
    file_type: SupportedFileType,
    page_number: int | None,
    section_title: str | None,
    chunk_index: int,
) -> str:
    if file_type == SupportedFileType.PDF and page_number is not None and page_number > 0:
        return f"{filename} — page {page_number}"
    if file_type in {SupportedFileType.DOCX, SupportedFileType.MARKDOWN} and section_title:
        return f"{filename} — {section_title}"
    if file_type == SupportedFileType.TXT:
        return f"{filename} — chunk {chunk_index + 1}"
    return filename


def _safe_filename(filename: str) -> str:
    name = PurePath(filename).name.strip()
    return name or "source"


def _safe_section(section_title: str | None) -> str | None:
    if section_title is None:
        return None
    cleaned = " ".join(section_title.split())
    if not cleaned:
        return None
    return cleaned[:120]
