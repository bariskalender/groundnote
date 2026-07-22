"""Document embedding indexing workflow."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Protocol

from groundnote.config import Settings
from groundnote.domain import Document, DocumentChunk, DocumentStatus
from groundnote.embeddings import (
    DocumentAlreadyIndexedError,
    DocumentNotReadyForIndexingError,
    EmbeddingService,
    IndexingError,
    IndexingResult,
)
from groundnote.performance import IndexingMetricsCollector, IndexingStage
from groundnote.storage import SerializedEmbedding, SQLiteUnitOfWork, serialize_embedding
from groundnote.utils import get_logger, safe_log_info, safe_log_warning, sanitize_log_fields


class UnitOfWorkFactory(Protocol):
    """Callable Unit of Work factory protocol by convention."""

    def __call__(self) -> SQLiteUnitOfWork: ...


class DocumentIndexingService:
    """Generate and persist local embeddings for one document."""

    def __init__(
        self,
        *,
        settings: Settings,
        unit_of_work_factory: UnitOfWorkFactory,
        embedding_service: EmbeddingService,
    ) -> None:
        self.settings = settings
        self.unit_of_work_factory = unit_of_work_factory
        self.embedding_service = embedding_service
        self.logger = get_logger(__name__)

    def index_document(
        self,
        document_id: str,
        *,
        force_reindex: bool = False,
        metrics: IndexingMetricsCollector | None = None,
    ) -> IndexingResult:
        """Index one document without holding a SQLite transaction during model inference."""
        started = time.perf_counter()
        collector = metrics or IndexingMetricsCollector(
            embedding_batch_size=self.settings.embedding_batch_size
        )
        chunks = self._prepare_for_indexing(document_id, force_reindex=force_reindex)
        collector.chunk_count = len(chunks)

        try:
            collector.model_reused = self.embedding_service.is_loaded
            with collector.measure(IndexingStage.LOADING_EMBEDDING_MODEL):
                self.embedding_service.load()
            serialized = self._embed_chunks(chunks, metrics=collector)
            embedded_at = datetime.now(UTC)
            with self.unit_of_work_factory() as unit_of_work:
                if unit_of_work.documents is None or unit_of_work.vectors is None:
                    raise RuntimeError("Unit of Work repositories are unavailable.")
                document = unit_of_work.documents.get_by_id(document_id)
                if document.status != DocumentStatus.INDEXING:
                    raise DocumentNotReadyForIndexingError("Document is no longer being indexed.")
                with collector.measure(IndexingStage.SAVING_VECTORS):
                    unit_of_work.vectors.save_chunk_embeddings(
                        [(chunk_id, embedding) for chunk_id, embedding in serialized],
                        embedding_model=self.settings.embedding_model,
                        embedding_version=self.settings.embedding_version,
                        embedded_at=embedded_at,
                        sync_fts=False,
                    )
                with collector.measure(IndexingStage.FTS_INDEXING):
                    unit_of_work.vectors.sync_fts_for_document(document_id)
                with collector.measure(IndexingStage.INTEGRITY_VERIFICATION):
                    integrity = unit_of_work.vectors.index_integrity(
                        document_id,
                        embedding_model=self.settings.embedding_model,
                        embedding_dimension=self.settings.embedding_dimension,
                        embedding_version=self.settings.embedding_version,
                        embedding_dtype=self.settings.embedding_dtype,
                    )
                if not integrity.is_complete:
                    raise IndexingError("The local index did not pass its final integrity check.")
                with collector.measure(IndexingStage.FINALIZATION):
                    indexed_document = document.model_copy(
                        update={
                            "status": DocumentStatus.INDEXED,
                            "updated_at": embedded_at,
                            "indexed_at": embedded_at,
                            "embedding_model": self.settings.embedding_model,
                            "embedding_dimension": self.settings.embedding_dimension,
                            "embedding_version": self.settings.embedding_version,
                            "error_message": None,
                        }
                    )
                    unit_of_work.documents.update(indexed_document)
                    unit_of_work.commit()
        except BaseException:
            self._unload_embedding_model()
            try:
                self._mark_failed(document_id, "Embedding generation failed during indexing.")
            except Exception as state_error:
                safe_log_warning(
                    self.logger,
                    "document_failure_state_update_failed",
                    document_id=document_id,
                    error_type=type(state_error).__name__,
                )
            raise
        finally:
            if not self.settings.keep_models_loaded:
                self._unload_embedding_model()

        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        diagnostics = collector.snapshot()
        safe_log_info(
            self.logger,
            "document_indexed",
            **sanitize_log_fields(
                {
                    "document_id": document_id,
                    "chunk_count": len(chunks),
                    "batch_count": _batch_count(len(chunks), self.settings.embedding_batch_size),
                    "embedding_model": self.settings.embedding_model,
                    "embedding_dimension": self.settings.embedding_dimension,
                    "dtype": self.settings.embedding_dtype,
                    "duration_ms": duration_ms,
                    "stage_durations_ms": diagnostics.stage_durations_ms,
                    "peak_process_rss_mb": diagnostics.peak_process_rss_mb,
                    "status": DocumentStatus.INDEXED.value,
                }
            ),
        )
        return IndexingResult(
            document_id=document_id,
            indexed_chunk_count=len(chunks),
            embedding_model=self.settings.embedding_model,
            embedding_dimension=self.settings.embedding_dimension,
            embedding_dtype=self.settings.embedding_dtype,
            status=DocumentStatus.INDEXED,
            warnings=[],
            duration_ms=duration_ms,
            diagnostics=diagnostics,
        )

    def _prepare_for_indexing(
        self,
        document_id: str,
        *,
        force_reindex: bool,
    ) -> list[DocumentChunk]:
        with self.unit_of_work_factory() as unit_of_work:
            if unit_of_work.documents is None or unit_of_work.vectors is None:
                raise RuntimeError("Unit of Work repositories are unavailable.")
            document = unit_of_work.documents.get_by_id(document_id)
            self._validate_status(document, force_reindex=force_reindex)
            chunks = unit_of_work.vectors.list_for_document(document_id)
            if not chunks:
                raise IndexingError("Document has no chunks to index.")
            if force_reindex:
                unit_of_work.vectors.clear_embeddings_for_document(document_id)
            elif unit_of_work.vectors.count_embedded_chunks_for_document(document_id) > 0:
                raise IndexingError("Document already has partial embeddings.")

            unit_of_work.documents.update(
                document.model_copy(
                    update={
                        "status": DocumentStatus.INDEXING,
                        "updated_at": datetime.now(UTC),
                        "error_message": None,
                    }
                )
            )
            unit_of_work.commit()
            return chunks

    def _mark_failed(self, document_id: str, safe_message: str) -> None:
        with self.unit_of_work_factory() as unit_of_work:
            if unit_of_work.documents is None or unit_of_work.vectors is None:
                raise RuntimeError("Unit of Work repositories are unavailable.")
            document = unit_of_work.documents.get_by_id(document_id)
            unit_of_work.vectors.clear_embeddings_for_document(document_id)
            unit_of_work.documents.update(
                document.model_copy(
                    update={
                        "status": DocumentStatus.FAILED,
                        "updated_at": datetime.now(UTC),
                        "indexed_at": None,
                        "embedding_model": None,
                        "embedding_dimension": None,
                        "embedding_version": None,
                        "error_message": safe_message,
                    }
                )
            )
            unit_of_work.commit()

    def _unload_embedding_model(self) -> None:
        try:
            self.embedding_service.unload()
        except Exception:
            safe_log_warning(
                self.logger,
                "embedding_model_unload_failed",
                embedding_model=self.settings.embedding_model,
            )

    def clear_embeddings(self, document_id: str) -> None:
        """Clear embeddings for one document and return it to PENDING_EMBEDDING."""
        with self.unit_of_work_factory() as unit_of_work:
            if unit_of_work.documents is None or unit_of_work.vectors is None:
                raise RuntimeError("Unit of Work repositories are unavailable.")
            document = unit_of_work.documents.get_by_id(document_id)
            unit_of_work.vectors.clear_embeddings_for_document(document_id)
            unit_of_work.documents.update(
                document.model_copy(
                    update={
                        "status": DocumentStatus.PENDING_EMBEDDING,
                        "updated_at": datetime.now(UTC),
                        "indexed_at": None,
                        "embedding_model": None,
                        "embedding_dimension": None,
                        "embedding_version": None,
                        "error_message": None,
                    }
                )
            )
            unit_of_work.commit()

    def get_indexing_status(self, document_id: str) -> DocumentStatus:
        """Return the current document indexing status."""
        with self.unit_of_work_factory() as unit_of_work:
            if unit_of_work.documents is None:
                raise RuntimeError("Unit of Work document repository is unavailable.")
            return unit_of_work.documents.get_by_id(document_id).status

    def _embed_chunks(
        self,
        chunks: list[DocumentChunk],
        *,
        metrics: IndexingMetricsCollector,
    ) -> list[tuple[str, SerializedEmbedding]]:
        serialized: list[tuple[str, SerializedEmbedding]] = []
        with metrics.measure(IndexingStage.EMBEDDING):
            for start in range(0, len(chunks), self.settings.embedding_batch_size):
                batch = chunks[start : start + self.settings.embedding_batch_size]
                result = self.embedding_service.embed_texts([chunk.content for chunk in batch])
                if result.input_count != len(batch):
                    raise IndexingError("Embedding provider returned the wrong number of vectors.")
                for chunk, vector in zip(batch, result.vectors, strict=True):
                    data, dimension, dtype = serialize_embedding(vector)
                    if dimension != self.settings.embedding_dimension:
                        raise IndexingError("Serialized embedding dimension mismatch.")
                    serialized.append(
                        (chunk.id, SerializedEmbedding(data=data, dimension=dimension, dtype=dtype))
                    )
                metrics.embedding_batch_count += 1
                metrics.progress(
                    IndexingStage.EMBEDDING,
                    completed_units=min(start + len(batch), len(chunks)),
                    total_units=len(chunks),
                    unit="chunks",
                )
        return serialized

    @staticmethod
    def _validate_status(document: Document, *, force_reindex: bool) -> None:
        if document.status == DocumentStatus.INDEXED and not force_reindex:
            raise DocumentAlreadyIndexedError("Document is already indexed.")
        if force_reindex and document.status in {DocumentStatus.INDEXED, DocumentStatus.FAILED}:
            return
        if document.status != DocumentStatus.PENDING_EMBEDDING:
            raise DocumentNotReadyForIndexingError("Document is not ready for indexing.")


def _batch_count(item_count: int, batch_size: int) -> int:
    return (item_count + batch_size - 1) // batch_size
