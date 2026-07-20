"""Pre-embedding document ingestion workflow."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from groundnote.chunking import (
    DocumentChunker,
    HybridRecursiveChunker,
    IngestionPlan,
    settings_to_chunking_settings,
)
from groundnote.chunking.service import text_chunk_to_document_chunk
from groundnote.config import Settings
from groundnote.documents import DocumentProcessingService, DuplicateCheckResult, DuplicateType
from groundnote.domain import Document, DocumentStatus
from groundnote.storage import SQLiteUnitOfWork
from groundnote.utils import get_logger, safe_log_info, sanitize_log_fields


class UnitOfWorkFactory(Protocol):
    """Create a fresh transaction-scoped Unit of Work."""

    def __call__(self) -> SQLiteUnitOfWork: ...


class PreEmbeddingIngestionService:
    """Validate, parse, chunk, and persist documents before embedding generation."""

    def __init__(
        self,
        *,
        settings: Settings,
        unit_of_work_factory: UnitOfWorkFactory,
        chunker: DocumentChunker | None = None,
    ) -> None:
        self.settings = settings
        self.unit_of_work_factory = unit_of_work_factory
        self.chunker = chunker or HybridRecursiveChunker()
        self.logger = get_logger(__name__)

    def ingest_file(
        self,
        file_path: Path,
        *,
        original_filename: str,
        allowed_directory: Path,
    ) -> IngestionPlan:
        """Persist document metadata and pre-embedding chunks in one transaction."""
        started = time.perf_counter()
        chunking_settings = settings_to_chunking_settings(self.settings)
        with self.unit_of_work_factory() as unit_of_work:
            if unit_of_work.documents is None or unit_of_work.vectors is None:
                raise RuntimeError("Unit of Work repositories are unavailable.")

            processing_service = DocumentProcessingService(
                settings=self.settings,
                duplicate_lookup=unit_of_work.documents,
            )
            parsed = processing_service.process_file(
                file_path,
                original_filename=original_filename,
                allowed_directory=allowed_directory,
                stored_filename=file_path.name,
            )
            chunking_result = self.chunker.chunk(parsed, chunking_settings)
            document_id = str(uuid.uuid4())
            now = datetime.now(UTC)
            document = Document(
                id=document_id,
                original_filename=parsed.original_filename,
                stored_filename=parsed.stored_filename,
                file_type=parsed.file_type,
                sha256=parsed.sha256,
                file_size_bytes=parsed.file_size_bytes,
                page_count=parsed.page_count,
                status=DocumentStatus.PENDING_EMBEDDING,
                created_at=now,
                updated_at=now,
                indexed_at=None,
                error_message=None,
                embedding_model=None,
                embedding_dimension=None,
                chunking_version=chunking_settings.version,
            )
            unit_of_work.documents.add(document)
            persisted_chunks = [
                text_chunk_to_document_chunk(chunk, document_id=document_id)
                for chunk in chunking_result.chunks
            ]
            unit_of_work.vectors.add_chunks([(chunk, None) for chunk in persisted_chunks])
            unit_of_work.commit()

        chunks = [
            chunk.model_copy(update={"document_id": document_id})
            for chunk in chunking_result.chunks
        ]
        plan = IngestionPlan(
            parsed_document=parsed,
            chunks=chunks,
            sha256=parsed.sha256,
            duplicate_status=DuplicateCheckResult(
                is_duplicate=False,
                existing_document_id=None,
                sha256=parsed.sha256,
                duplicate_type=DuplicateType.NONE,
                user_message="No exact duplicate was found.",
            ),
            document_status=DocumentStatus.PENDING_EMBEDDING,
            embedding_model=None,
            embedding_dimension=None,
            created_at=datetime.now(UTC),
            warnings=[*parsed.warnings, *chunking_result.warnings],
        )
        self._log_success(
            safe_filename=parsed.original_filename,
            file_type=parsed.file_type.value,
            section_count=len(parsed.sections),
            chunk_count=len(chunks),
            chunk_sizes=[chunk.character_count for chunk in chunks],
            warning_count=len(plan.warnings),
            chunking_version=chunking_settings.version,
            duration_ms=round((time.perf_counter() - started) * 1000, 3),
        )
        return plan

    def _log_success(
        self,
        *,
        safe_filename: str,
        file_type: str,
        section_count: int,
        chunk_count: int,
        chunk_sizes: list[int],
        warning_count: int,
        chunking_version: str,
        duration_ms: float,
    ) -> None:
        average_size = round(sum(chunk_sizes) / len(chunk_sizes), 2) if chunk_sizes else 0
        safe_log_info(
            self.logger,
            "document_pre_embedding_ingested",
            **sanitize_log_fields(
                {
                    "safe_filename": safe_filename,
                    "file_type": file_type,
                    "section_count": section_count,
                    "chunk_count": chunk_count,
                    "average_chunk_size": average_size,
                    "minimum_chunk_size": min(chunk_sizes) if chunk_sizes else 0,
                    "maximum_chunk_size": max(chunk_sizes) if chunk_sizes else 0,
                    "warning_count": warning_count,
                    "chunking_version": chunking_version,
                    "duration_ms": duration_ms,
                    "status": DocumentStatus.PENDING_EMBEDDING.value,
                }
            ),
        )
