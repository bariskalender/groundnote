"""Storage package for GroundNote."""

from groundnote.storage.connection import SQLiteConnectionFactory
from groundnote.storage.embedding_codec import deserialize_embedding, serialize_embedding
from groundnote.storage.exceptions import (
    DocumentNotFoundError,
    DuplicateDocumentError,
    InvalidEmbeddingError,
    MigrationError,
    StorageError,
)
from groundnote.storage.migrations import MigrationRunner
from groundnote.storage.repositories import (
    DocumentIndexIntegrity,
    DocumentRepository,
    LexicalChunkMatch,
    SearchableChunkEmbedding,
    SerializedEmbedding,
    SQLiteDocumentRepository,
    SQLiteVectorRepository,
    VectorRepository,
)
from groundnote.storage.unit_of_work import SQLiteUnitOfWork, SQLiteUnitOfWorkFactory

__all__ = [
    "DocumentNotFoundError",
    "DocumentIndexIntegrity",
    "DocumentRepository",
    "DuplicateDocumentError",
    "InvalidEmbeddingError",
    "LexicalChunkMatch",
    "MigrationError",
    "MigrationRunner",
    "SQLiteConnectionFactory",
    "SQLiteDocumentRepository",
    "SQLiteUnitOfWork",
    "SQLiteUnitOfWorkFactory",
    "SQLiteVectorRepository",
    "SearchableChunkEmbedding",
    "SerializedEmbedding",
    "StorageError",
    "VectorRepository",
    "deserialize_embedding",
    "serialize_embedding",
]
