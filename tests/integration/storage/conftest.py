from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from groundnote.domain import Document, DocumentChunk, DocumentStatus, SupportedFileType
from groundnote.storage import MigrationRunner, SQLiteConnectionFactory


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    return tmp_path / "groundnote.sqlite3"


@pytest.fixture
def initialized_database(database_path: Path) -> Path:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    factory = SQLiteConnectionFactory(database_path)
    with factory.open() as connection:
        MigrationRunner().apply(connection)
    return database_path


def make_document(document_id: str = "doc-1", sha256: str | None = None) -> Document:
    return Document(
        id=document_id,
        original_filename=f"{document_id}.pdf",
        stored_filename=f"{document_id}.pdf",
        file_type=SupportedFileType.PDF,
        sha256=sha256 or ("a" * 64),
        file_size_bytes=100,
        status=DocumentStatus.PENDING,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def make_chunk(
    chunk_id: str = "chunk-1",
    document_id: str = "doc-1",
    chunk_index: int = 0,
) -> DocumentChunk:
    return DocumentChunk(
        id=chunk_id,
        document_id=document_id,
        chunk_index=chunk_index,
        content="A small chunk.",
        page_number=1,
        character_count=14,
        created_at=datetime.now(UTC),
    )
