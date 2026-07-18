from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from groundnote.domain import (
    Document,
    DocumentChunk,
    DocumentStatus,
    RetrievalResult,
    SupportedFileType,
)

VALID_SHA = "a" * 64


def test_document_accepts_valid_values() -> None:
    document = Document(
        id="doc-1",
        original_filename="notes.pdf",
        stored_filename="doc-1.pdf",
        file_type=SupportedFileType.PDF,
        sha256=VALID_SHA,
        file_size_bytes=10,
        status=DocumentStatus.PENDING,
    )

    assert document.sha256 == VALID_SHA
    assert document.created_at.tzinfo is not None
    assert "doc-1.pdf" not in repr(document)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"sha256": "bad"},
        {"page_count": 0},
        {"embedding_dimension": 0},
        {"file_size_bytes": -1},
    ],
)
def test_document_rejects_invalid_values(kwargs: dict[str, object]) -> None:
    values = {
        "id": "doc-1",
        "original_filename": "notes.pdf",
        "stored_filename": "doc-1.pdf",
        "file_type": SupportedFileType.PDF,
        "sha256": VALID_SHA,
        "file_size_bytes": 10,
    }
    values.update(kwargs)
    with pytest.raises(ValidationError):
        Document(**values)


def test_document_rejects_naive_timestamps() -> None:
    with pytest.raises(ValidationError):
        Document(
            id="doc-1",
            original_filename="notes.pdf",
            stored_filename="doc-1.pdf",
            file_type=SupportedFileType.PDF,
            sha256=VALID_SHA,
            file_size_bytes=10,
            created_at=datetime(2026, 1, 1),
        )


def test_chunk_and_retrieval_models_validate_ranges() -> None:
    chunk = DocumentChunk(
        id="chunk-1",
        document_id="doc-1",
        chunk_index=0,
        content="hello",
        character_count=5,
        created_at=datetime.now(UTC),
    )
    result = RetrievalResult(
        chunk_id=chunk.id,
        document_id=chunk.document_id,
        filename="notes.pdf",
        content=chunk.content,
        similarity_score=0.5,
        rank=1,
    )

    assert result.rank == 1
    with pytest.raises(ValidationError):
        RetrievalResult(
            chunk_id="chunk-1",
            document_id="doc-1",
            filename="notes.pdf",
            content="hello",
            similarity_score=2.0,
            rank=1,
        )
