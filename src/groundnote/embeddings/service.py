"""Embedding provider adapter with validation and normalization."""

from __future__ import annotations

import time
from collections.abc import Sequence

import numpy as np

from groundnote.config import Settings
from groundnote.embeddings.errors import (
    EmbeddingGenerationError,
    EmbeddingModelLoadError,
    EmptyEmbeddingInputError,
)
from groundnote.embeddings.models import (
    BatchEmbeddingProvider,
    EmbeddingBatchResult,
    EmbeddingVector,
)
from groundnote.embeddings.validation import (
    validate_and_normalize_matrix,
    validate_and_normalize_vector,
)


class EmbeddingService:
    """Generate validated normalized embeddings through a provider."""

    def __init__(self, *, settings: Settings, provider: BatchEmbeddingProvider) -> None:
        self.settings = settings
        self.provider = provider
        self._loaded = False

    def load(self) -> None:
        """Load the embedding provider."""
        if self._loaded:
            return
        try:
            self.provider.load()
            self._loaded = True
        except Exception as exc:
            self._loaded = False
            raise EmbeddingModelLoadError("Embedding model could not be loaded.") from exc

    @property
    def is_loaded(self) -> bool:
        """Return GroundNote's tracked provider state without querying the SDK."""
        return self._loaded

    def unload(self) -> None:
        """Release embedding provider resources where supported."""
        try:
            self.provider.unload()
        finally:
            self._loaded = False

    def embed_texts(self, texts: Sequence[str]) -> EmbeddingBatchResult:
        """Embed a non-empty batch while preserving input order."""
        cleaned = [text for text in texts]
        if not cleaned:
            raise EmptyEmbeddingInputError("Embedding input batch must not be empty.")
        if any(not text.strip() for text in cleaned):
            raise EmptyEmbeddingInputError("Embedding inputs must not be empty.")
        started = time.perf_counter()
        try:
            raw = self.provider.embed_many(cleaned, batch_size=self.settings.embedding_batch_size)
            raw_vectors = np.asarray(raw.vectors, dtype=np.float32)
        except Exception as exc:
            raise EmbeddingGenerationError("Embedding generation failed.") from exc
        vectors = validate_and_normalize_matrix(
            raw_vectors,
            expected_dimension=self.settings.embedding_dimension,
            expected_count=len(cleaned),
            dtype=self.settings.embedding_dtype,
        )
        return EmbeddingBatchResult(
            vectors=vectors,
            model=self.settings.embedding_model,
            dimension=self.settings.embedding_dimension,
            dtype=self.settings.embedding_dtype,
            input_count=len(cleaned),
            duration_ms=round((time.perf_counter() - started) * 1000, 3),
            warnings=[],
        )

    def embed_query(self, text: str) -> EmbeddingVector:
        """Embed one query text with the same validation policy as stored vectors."""
        cleaned = text.strip()
        if not cleaned:
            raise EmptyEmbeddingInputError("Query text must not be empty.")
        try:
            raw_vector = self.provider.embed_one(cleaned)
        except Exception as exc:
            raise EmbeddingGenerationError("Query embedding generation failed.") from exc
        vector = validate_and_normalize_vector(
            raw_vector,
            expected_dimension=self.settings.embedding_dimension,
            dtype=self.settings.embedding_dtype,
        )
        return EmbeddingVector(
            values=vector,
            dimension=self.settings.embedding_dimension,
            dtype=self.settings.embedding_dtype,
            model=self.settings.embedding_model,
            version=self.settings.embedding_version,
        )
