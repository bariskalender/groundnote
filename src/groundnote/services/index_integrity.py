"""Document index integrity checks and restart recovery."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from groundnote.config import Settings
from groundnote.domain import Document, DocumentStatus
from groundnote.services.indexing import UnitOfWorkFactory
from groundnote.services.indexing_ownership import ActiveIndexingRegistry
from groundnote.storage import VectorRepository
from groundnote.utils import get_logger, safe_log_info

TRANSIENT_DOCUMENT_STATUSES = {
    DocumentStatus.PENDING,
    DocumentStatus.PARSING,
    DocumentStatus.PARSED,
    DocumentStatus.PENDING_EMBEDDING,
    DocumentStatus.INDEXING,
}
INTERRUPTED_INDEXING_MESSAGE = (
    "Indexing was interrupted. Re-index this document to make it available."
)
INCOMPLETE_INDEX_MESSAGE = (
    "The local index is incomplete. Re-index this document to make it available."
)


@dataclass(frozen=True)
class IndexRecoveryResult:
    """Privacy-safe reconciliation counts returned to bootstrap and tests."""

    inspected_count: int
    interrupted_count: int
    incomplete_count: int

    @property
    def recovered_count(self) -> int:
        return self.interrupted_count + self.incomplete_count


class DocumentIndexIntegrityService:
    """Reconcile stale states and prove that Ready documents have a complete index."""

    def __init__(
        self,
        *,
        settings: Settings,
        unit_of_work_factory: UnitOfWorkFactory,
        indexing_registry: ActiveIndexingRegistry | None = None,
    ) -> None:
        self.settings = settings
        self.unit_of_work_factory = unit_of_work_factory
        if indexing_registry is None:
            if settings.database_path is None:
                raise RuntimeError("Database path is not configured.")
            indexing_registry = ActiveIndexingRegistry(settings.database_path)
        self.indexing_registry = indexing_registry
        self.logger = get_logger(__name__)

    def reconcile(self, *, recover_transient: bool = True) -> IndexRecoveryResult:
        """Mark transient or incomplete indexes retryable in one idempotent transaction."""
        interrupted_count = 0
        incomplete_count = 0
        active_document_ids = self.indexing_registry.active_document_ids()
        pipeline_is_active = self.indexing_registry.pipeline_is_active()
        with self.unit_of_work_factory() as unit_of_work:
            if unit_of_work.documents is None or unit_of_work.vectors is None:
                raise RuntimeError("Unit of Work repositories are unavailable.")
            documents = unit_of_work.documents.list_all()
            for document in documents:
                if document.id in active_document_ids:
                    continue
                safe_message: str | None = None
                if (
                    recover_transient
                    and not pipeline_is_active
                    and document.status in TRANSIENT_DOCUMENT_STATUSES
                ):
                    safe_message = INTERRUPTED_INDEXING_MESSAGE
                    interrupted_count += 1
                elif document.status is DocumentStatus.INDEXED and not self._is_complete(
                    document,
                    unit_of_work.vectors,
                ):
                    safe_message = INCOMPLETE_INDEX_MESSAGE
                    incomplete_count += 1
                if safe_message is None:
                    continue
                unit_of_work.vectors.clear_embeddings_for_document(document.id)
                unit_of_work.documents.update(_failed_document(document, safe_message))
            if interrupted_count or incomplete_count:
                unit_of_work.commit()

        result = IndexRecoveryResult(
            inspected_count=len(documents),
            interrupted_count=interrupted_count,
            incomplete_count=incomplete_count,
        )
        if result.recovered_count:
            safe_log_info(
                self.logger,
                "document_index_recovery_completed",
                inspected_count=result.inspected_count,
                interrupted_count=result.interrupted_count,
                incomplete_count=result.incomplete_count,
            )
        return result

    def _is_complete(self, document: Document, vectors: VectorRepository) -> bool:
        integrity = vectors.index_integrity(
            document.id,
            embedding_model=self.settings.embedding_model,
            embedding_dimension=self.settings.embedding_dimension,
            embedding_version=self.settings.embedding_version,
            embedding_dtype=self.settings.embedding_dtype,
        )
        return (
            document.indexed_at is not None
            and document.embedding_model == self.settings.embedding_model
            and document.embedding_dimension == self.settings.embedding_dimension
            and document.embedding_version == self.settings.embedding_version
            and integrity.is_complete
        )


def _failed_document(document: Document, safe_message: str) -> Document:
    return document.model_copy(
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
