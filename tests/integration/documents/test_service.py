from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from groundnote.config import Settings
from groundnote.documents import DocumentError, DocumentProcessingService
from groundnote.documents.hashing import calculate_sha256
from groundnote.domain import Document, DocumentStatus, SupportedFileType
from groundnote.storage import MigrationRunner, SQLiteConnectionFactory, SQLiteDocumentRepository

from .conftest import write_docx, write_text_pdf


def test_document_service_processes_all_supported_formats(document_dir: Path) -> None:
    settings = Settings(data_directory=document_dir / "app")
    files = [
        (write_text_pdf(document_dir / "notes.pdf", ["PDF text"]), "notes.pdf"),
        (write_docx(document_dir / "notes.docx"), "notes.docx"),
        (_write(document_dir / "notes.txt", "TXT text"), "notes.txt"),
        (_write(document_dir / "notes.md", "# Heading\n\n```python\nx = 1\n```"), "notes.md"),
    ]

    service = DocumentProcessingService(settings=settings)

    parsed = [
        service.process_file(path, original_filename=name, allowed_directory=document_dir)
        for path, name in files
    ]

    assert [item.file_type for item in parsed] == [
        SupportedFileType.PDF,
        SupportedFileType.DOCX,
        SupportedFileType.TXT,
        SupportedFileType.MARKDOWN,
    ]
    assert all(item.sections for item in parsed)


def test_duplicate_precheck_uses_sqlite_and_skips_parsing(
    document_dir: Path,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "groundnote.sqlite3"
    factory = SQLiteConnectionFactory(database_path)
    with factory.open() as connection:
        MigrationRunner().apply(connection)
        repository = SQLiteDocumentRepository(connection)
        path = _write(document_dir / "duplicate.txt", "duplicate text")
        sha256 = calculate_sha256(path)
        repository.add(
            Document(
                id="existing",
                original_filename="duplicate.txt",
                stored_filename="stored.txt",
                file_type=SupportedFileType.TXT,
                sha256=sha256,
                file_size_bytes=path.stat().st_size,
                status=DocumentStatus.PARSED,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        service = DocumentProcessingService(
            settings=Settings(data_directory=tmp_path / "app"),
            duplicate_lookup=repository,
        )

        with pytest.raises(DocumentError, match="exact duplicate"):
            service.process_file(
                path,
                original_filename="duplicate.txt",
                allowed_directory=document_dir,
            )


def test_service_errors_are_user_safe_and_no_partial_database_state(
    document_dir: Path,
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "groundnote.sqlite3"
    factory = SQLiteConnectionFactory(database_path)
    with factory.open() as connection:
        MigrationRunner().apply(connection)
        repository = SQLiteDocumentRepository(connection)
        path = document_dir / "corrupt.pdf"
        path.write_bytes(b"%PDF- corrupt")
        service = DocumentProcessingService(
            settings=Settings(data_directory=tmp_path / "app"),
            duplicate_lookup=repository,
        )

        with pytest.raises(DocumentError) as exc_info:
            service.process_file(
                path,
                original_filename="corrupt.pdf",
                allowed_directory=document_dir,
            )

        assert str(tmp_path) not in str(exc_info.value)
        assert repository.count() == 0


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path
