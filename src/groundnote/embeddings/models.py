"""Provider-neutral embedding and indexing models."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np
import numpy.typing as npt

from groundnote.domain import DocumentStatus

Float32Vector = npt.NDArray[np.float32]
Float32Matrix = npt.NDArray[np.float32]


@dataclass(frozen=True)
class EmbeddingVector:
    """Validated normalized embedding vector."""

    values: Float32Vector
    dimension: int
    dtype: str
    model: str
    version: str


@dataclass(frozen=True)
class EmbeddingBatchResult:
    """Validated embedding vectors for a batch of input texts."""

    vectors: Float32Matrix
    model: str
    dimension: int
    dtype: str
    input_count: int
    duration_ms: float
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class IndexingResult:
    """Result of indexing one document."""

    document_id: str
    indexed_chunk_count: int
    embedding_model: str
    embedding_dimension: int
    embedding_dtype: str
    status: DocumentStatus
    warnings: list[str]
    duration_ms: float


class BatchEmbeddingProvider(Protocol):
    """Minimal embedding provider behavior required by indexing and retrieval."""

    model_alias: str
    dimension: int | None

    def load(self) -> None: ...
    def embed_many(self, texts: Sequence[str], *, batch_size: int = 8) -> ProviderBatchResult: ...
    def embed_one(self, text: str) -> npt.NDArray[np.float32]: ...
    def unload(self) -> None: ...


class ProviderBatchResult(Protocol):
    """Provider batch result with vector matrix."""

    vectors: npt.NDArray[np.float32]
