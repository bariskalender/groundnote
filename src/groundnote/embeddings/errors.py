"""Embedding, indexing, and vector validation errors."""

from __future__ import annotations


class EmbeddingError(Exception):
    """Base embedding error with user-safe messages."""


class EmbeddingProviderUnavailableError(EmbeddingError):
    """Raised when an embedding provider is unavailable."""


class EmbeddingModelLoadError(EmbeddingError):
    """Raised when an embedding model cannot be loaded."""


class EmbeddingGenerationError(EmbeddingError):
    """Raised when embedding generation fails."""


class EmbeddingDimensionMismatchError(EmbeddingError):
    """Raised when vector dimensions are inconsistent."""


class InvalidEmbeddingError(EmbeddingError):
    """Raised when an embedding vector is malformed."""


class EmptyEmbeddingInputError(EmbeddingError):
    """Raised when embedding input is empty."""


class IndexingError(EmbeddingError):
    """Raised when document indexing cannot complete."""


class DocumentNotReadyForIndexingError(IndexingError):
    """Raised when a document status cannot begin indexing."""


class DocumentAlreadyIndexedError(IndexingError):
    """Raised when an indexed document is indexed again without force."""


class VectorDecodeError(EmbeddingError):
    """Raised when a persisted vector cannot be decoded safely."""


class UnsupportedEmbeddingDtypeError(EmbeddingError):
    """Raised when an embedding dtype is unsupported."""
