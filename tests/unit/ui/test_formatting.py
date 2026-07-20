from __future__ import annotations

from datetime import UTC, datetime

import pytest

from groundnote.domain import DocumentStatus, SupportedFileType
from groundnote.rag import Citation
from groundnote.ui.formatting import (
    citation_to_view,
    format_duration,
    format_file_size,
    format_status,
    format_timestamp,
    safe_filename,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, "0 B"), (1024, "1.0 KB"), (1_572_864, "1.5 MB"), (None, "Not available")],
)
def test_file_size_formatting(value: int | None, expected: str) -> None:
    assert format_file_size(value) == expected


def test_duration_timestamp_status_and_missing_values() -> None:
    timestamp = datetime(2026, 7, 20, 12, 30, tzinfo=UTC)

    assert format_duration(950) == "950 ms"
    assert format_duration(1250) == "1.25 s"
    assert format_duration(None) == "Not available"
    assert format_timestamp(timestamp) == "2026-07-20 12:30 UTC"
    assert format_timestamp(None) == "Not available"
    assert format_status(DocumentStatus.PENDING_EMBEDDING) == "Waiting for indexing"
    assert format_status(DocumentStatus.INDEXED) == "Ready"


def test_safe_filename_removes_paths_and_truncates_visually() -> None:
    assert safe_filename(r"C:\private\lecture.pdf") == "lecture.pdf"
    assert safe_filename("a" * 32 + "_lecture.pdf") == "lecture.pdf"
    rendered = safe_filename("a" * 100 + ".pdf", maximum_length=30)
    assert len(rendered) == 30
    assert rendered.endswith(".pdf")
    assert "/" not in rendered and "\\" not in rendered


@pytest.mark.parametrize(
    ("file_type", "page", "section", "expected"),
    [
        (SupportedFileType.PDF, 3, None, "lecture.pdf — page 3"),
        (SupportedFileType.DOCX, None, "Dynamic Programming", "lecture.pdf — Dynamic Programming"),
        (SupportedFileType.MARKDOWN, None, "Vector Search", "lecture.pdf — Vector Search"),
        (SupportedFileType.TXT, None, None, "lecture.pdf — chunk 4"),
    ],
)
def test_citation_mapping_uses_structured_metadata(
    file_type: SupportedFileType,
    page: int | None,
    section: str | None,
    expected: str,
) -> None:
    citation = Citation(
        citation_id="S1",
        document_id="doc",
        chunk_id="chunk",
        source_filename=r"C:\stored\lecture.pdf",
        source_file_type=file_type,
        page_number=page,
        section_title=section,
        chunk_index=3,
        display_label="untrusted stored label",
        score=0.75,
    )

    view = citation_to_view(citation)

    assert view.label == expected
    assert "stored" not in view.label
    assert "/" not in view.label and "\\" not in view.label
    assert view.citation_id == "S1"
