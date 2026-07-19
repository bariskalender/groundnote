"""Embedding validation and service package."""

from groundnote.embeddings.errors import (
    DocumentAlreadyIndexedError,
    DocumentNotReadyForIndexingError,
    EmbeddingDimensionMismatchError,
    EmbeddingError,
    EmbeddingGenerationError,
    EmbeddingModelLoadError,
    EmbeddingProviderUnavailableError,
    EmptyEmbeddingInputError,
    IndexingError,
    InvalidEmbeddingError,
    UnsupportedEmbeddingDtypeError,
    VectorDecodeError,
)
from groundnote.embeddings.models import EmbeddingBatchResult, EmbeddingVector, IndexingResult
from groundnote.embeddings.service import EmbeddingService
from groundnote.embeddings.validation import (
    validate_and_normalize_matrix,
    validate_and_normalize_vector,
)

__all__ = [
    "DocumentAlreadyIndexedError",
    "DocumentNotReadyForIndexingError",
    "EmbeddingBatchResult",
    "EmbeddingDimensionMismatchError",
    "EmbeddingError",
    "EmbeddingGenerationError",
    "EmbeddingModelLoadError",
    "EmbeddingProviderUnavailableError",
    "EmbeddingService",
    "EmbeddingVector",
    "EmptyEmbeddingInputError",
    "IndexingError",
    "IndexingResult",
    "InvalidEmbeddingError",
    "UnsupportedEmbeddingDtypeError",
    "VectorDecodeError",
    "validate_and_normalize_matrix",
    "validate_and_normalize_vector",
]
