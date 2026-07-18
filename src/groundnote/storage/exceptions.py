"""Storage-specific exceptions."""

from __future__ import annotations


class StorageError(RuntimeError):
    """Base error for storage failures."""


class DocumentNotFoundError(StorageError):
    """Raised when a document cannot be found."""


class DuplicateDocumentError(StorageError):
    """Raised when a document violates duplicate constraints."""


class InvalidEmbeddingError(StorageError):
    """Raised when an embedding cannot be serialized or decoded safely."""


class MigrationError(StorageError):
    """Raised when schema migration fails."""
