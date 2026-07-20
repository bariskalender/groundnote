from __future__ import annotations

from datetime import UTC, datetime

import pytest

from groundnote.domain import DocumentStatus, SupportedFileType
from groundnote.ui.errors import InvalidFilterError
from groundnote.ui.models import DocumentSummary
from groundnote.ui.workflows import build_rag_request


def _document(document_id: str, file_type: SupportedFileType) -> DocumentSummary:
    return DocumentSummary(
        document_id=document_id,
        original_filename=f"{document_id}.{file_type.value}",
        file_type=file_type,
        status=DocumentStatus.INDEXED,
        file_size_bytes=10,
        page_count=None,
        chunk_count=1,
        embedded_chunk_count=1,
        created_at=datetime.now(UTC),
        indexed_at=datetime.now(UTC),
        embedding_model="fake",
    )


def test_empty_filters_mean_all_indexed_documents() -> None:
    indexed = [_document("one", SupportedFileType.PDF)]

    request = build_rag_request(
        "question",
        indexed_documents=indexed,
        document_ids=[],
        file_types=[],
    )

    assert request.document_ids is None
    assert request.file_types is None


def test_selected_filters_are_deduplicated_and_forwarded() -> None:
    indexed = [
        _document("one", SupportedFileType.PDF),
        _document("two", SupportedFileType.MARKDOWN),
    ]

    request = build_rag_request(
        "question",
        indexed_documents=indexed,
        document_ids=["two", "two"],
        file_types=[SupportedFileType.MARKDOWN, SupportedFileType.MARKDOWN],
    )

    assert request.document_ids == ["two"]
    assert request.file_types == [SupportedFileType.MARKDOWN]


def test_uncontrolled_document_id_is_rejected() -> None:
    indexed = [_document("one", SupportedFileType.PDF)]

    with pytest.raises(InvalidFilterError):
        build_rag_request(
            "question",
            indexed_documents=indexed,
            document_ids=["not-indexed"],
            file_types=[],
        )
