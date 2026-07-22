"""Application service coordinators."""

from groundnote.services.index_integrity import (
    DocumentIndexIntegrityService,
    IndexRecoveryResult,
)
from groundnote.services.indexing import DocumentIndexingService
from groundnote.services.indexing_ownership import (
    ActiveIndexingRegistry,
    IndexingOperationActiveError,
)
from groundnote.services.ingestion import PreEmbeddingIngestionService

__all__ = [
    "DocumentIndexIntegrityService",
    "DocumentIndexingService",
    "ActiveIndexingRegistry",
    "IndexingOperationActiveError",
    "IndexRecoveryResult",
    "PreEmbeddingIngestionService",
]
