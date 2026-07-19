from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from groundnote.chunking import ChunkingSettings, DocumentChunker
from groundnote.chunking.errors import ChunkingError
from groundnote.chunking.models import ChunkingResult
from groundnote.config import Settings
from groundnote.documents import DocumentError, ParsedDocument
from groundnote.documents.hashing import calculate_sha256
from groundnote.domain import Document, DocumentStatus, SupportedFileType
from groundnote.services import PreEmbeddingIngestionService
from groundnote.storage import (
    MigrationRunner,
    SQLiteConnectionFactory,
    SQLiteDocumentRepository,
    SQLiteUnitOfWorkFactory,
    SQLiteVectorRepository,
)
from tests.integration.documents.conftest import write_docx, write_text_pdf


class FailingChunker:
    def chunk(
        self,
        document: ParsedDocument,
        settings: ChunkingSettings,
    ) -> ChunkingResult:
        raise ChunkingError("Synthetic chunking failure.")


@pytest.fixture
def initialized_database(tmp_path: Path) -> Path:
    database_path = tmp_path / "groundnote.sqlite3"
    with SQLiteConnectionFactory(database_path).open() as connection:
        MigrationRunner().apply(connection)
    return database_path


def test_ingests_all_supported_formats_without_embeddings(
    tmp_path: Path,
    initialized_database: Path,
) -> None:
    document_dir = tmp_path / "documents"
    document_dir.mkdir()
    files = [
        (write_text_pdf(document_dir / "notes.pdf", ["PDF page one", "PDF page two"]), "notes.pdf"),
        (write_docx(document_dir / "notes.docx"), "notes.docx"),
        (
            _write(document_dir / "notes.txt", "TXT paragraph one.\n\nTXT paragraph two."),
            "notes.txt",
        ),
        (
            _write(document_dir / "notes.md", "# Heading\n\nMarkdown body.\n\n## Next\n\nMore."),
            "notes.md",
        ),
    ]
    service = _service(tmp_path, initialized_database)

    plans = [
        service.ingest_file(path, original_filename=name, allowed_directory=document_dir)
        for path, name in files
    ]

    with SQLiteConnectionFactory(initialized_database).open() as connection:
        documents = SQLiteDocumentRepository(connection)
        vectors = SQLiteVectorRepository(connection)
        rows = connection.execute(
            """
            SELECT embedding, embedding_dimension, embedding_dtype
            FROM document_chunks
            """
        ).fetchall()

        assert documents.count() == 4
        assert documents.count_by_status(DocumentStatus.PENDING_EMBEDDING) == 4
        assert vectors.count_chunks() == sum(len(plan.chunks) for plan in plans)
        assert vectors.list_all_embeddings() == []
        assert all(row["embedding"] is None for row in rows)
        assert all(row["embedding_dimension"] is None for row in rows)
        assert all(row["embedding_dtype"] is None for row in rows)

    assert [plan.document_status for plan in plans] == [DocumentStatus.PENDING_EMBEDDING] * 4
    assert all(plan.embedding_model is None for plan in plans)
    assert all(plan.embedding_dimension is None for plan in plans)


def test_pdf_page_metadata_and_markdown_heading_metadata_are_preserved(
    tmp_path: Path,
    initialized_database: Path,
) -> None:
    document_dir = tmp_path / "documents"
    document_dir.mkdir()
    pdf = write_text_pdf(document_dir / "pages.pdf", ["Page one text.", "Page two text."])
    markdown = _write(document_dir / "headings.md", "# Intro\n\nBody.\n\n## Details\n\nMore body.")
    service = _service(tmp_path, initialized_database)

    pdf_plan = service.ingest_file(
        pdf,
        original_filename="pages.pdf",
        allowed_directory=document_dir,
    )
    markdown_plan = service.ingest_file(
        markdown,
        original_filename="headings.md",
        allowed_directory=document_dir,
    )

    assert {chunk.page_number for chunk in pdf_plan.chunks} == {1, 2}
    assert "Intro" in {chunk.section_title for chunk in markdown_plan.chunks}
    assert "Details" in {chunk.section_title for chunk in markdown_plan.chunks}
    assert all(chunk.source_start_order <= chunk.source_end_order for chunk in markdown_plan.chunks)


def test_duplicate_precheck_skips_expensive_processing_and_creates_no_new_state(
    tmp_path: Path,
    initialized_database: Path,
) -> None:
    document_dir = tmp_path / "documents"
    document_dir.mkdir()
    path = _write(document_dir / "duplicate.txt", "duplicate text")
    sha256 = calculate_sha256(path)
    with SQLiteConnectionFactory(initialized_database).open() as connection:
        SQLiteDocumentRepository(connection).add(
            Document(
                id="existing",
                original_filename="duplicate.txt",
                stored_filename="stored.txt",
                file_type=SupportedFileType.TXT,
                sha256=sha256,
                file_size_bytes=path.stat().st_size,
                status=DocumentStatus.PENDING_EMBEDDING,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
    service = _service(tmp_path, initialized_database)

    with pytest.raises(DocumentError, match="exact duplicate"):
        service.ingest_file(path, original_filename="duplicate.txt", allowed_directory=document_dir)

    with SQLiteConnectionFactory(initialized_database).open() as connection:
        assert SQLiteDocumentRepository(connection).count() == 1
        assert SQLiteVectorRepository(connection).count_chunks() == 0


def test_parser_failure_rolls_back(tmp_path: Path, initialized_database: Path) -> None:
    document_dir = tmp_path / "documents"
    document_dir.mkdir()
    path = document_dir / "corrupt.pdf"
    path.write_bytes(b"%PDF- corrupt")
    service = _service(tmp_path, initialized_database)

    with pytest.raises(DocumentError):
        service.ingest_file(path, original_filename="corrupt.pdf", allowed_directory=document_dir)

    _assert_empty_database(initialized_database)


def test_chunking_failure_rolls_back(tmp_path: Path, initialized_database: Path) -> None:
    document_dir = tmp_path / "documents"
    document_dir.mkdir()
    path = _write(document_dir / "notes.txt", "A valid text file.")
    service = _service(tmp_path, initialized_database, chunker=FailingChunker())

    with pytest.raises(ChunkingError):
        service.ingest_file(path, original_filename="notes.txt", allowed_directory=document_dir)

    _assert_empty_database(initialized_database)


def test_successful_status_is_not_indexed_and_logs_do_not_include_full_content(
    tmp_path: Path,
    initialized_database: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    document_dir = tmp_path / "documents"
    document_dir.mkdir()
    secret_text = "PRIVATE COURSE SENTENCE SHOULD NOT APPEAR IN LOGS"
    path = _write(document_dir / "safe.txt", secret_text)
    service = _service(tmp_path, initialized_database)

    plan = service.ingest_file(path, original_filename="safe.txt", allowed_directory=document_dir)

    with SQLiteConnectionFactory(initialized_database).open() as connection:
        document = SQLiteDocumentRepository(connection).get_by_sha256(plan.sha256)
        assert document is not None
        assert document.status == DocumentStatus.PENDING_EMBEDDING
        assert document.indexed_at is None
    assert secret_text not in caplog.text


def _service(
    tmp_path: Path,
    database_path: Path,
    *,
    chunker: DocumentChunker | None = None,
) -> PreEmbeddingIngestionService:
    return PreEmbeddingIngestionService(
        settings=Settings(data_directory=tmp_path / "app"),
        unit_of_work_factory=SQLiteUnitOfWorkFactory(database_path),
        chunker=chunker,
    )


def _assert_empty_database(database_path: Path) -> None:
    with SQLiteConnectionFactory(database_path).open() as connection:
        assert SQLiteDocumentRepository(connection).count() == 0
        assert SQLiteVectorRepository(connection).count_chunks() == 0


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path
