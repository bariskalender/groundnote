"""Foundry Local embedding provider."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

import numpy as np

from groundnote.ai.errors import FoundryProviderError
from groundnote.ai.foundry_manager import FoundryManager
from groundnote.ai.interfaces import Float32Vector
from groundnote.ai.models import EmbeddingBatchResult, ModelInfo


class FoundryEmbeddingProvider:
    """Embedding provider backed by Microsoft Foundry Local."""

    def __init__(self, model_alias: str, manager: FoundryManager | None = None) -> None:
        self.model_alias = model_alias
        self.dimension: int | None = None
        self._manager = manager or FoundryManager()
        self._model: Any | None = None
        self._client: Any | None = None

    def ensure_model_available(self, *, download: bool = False) -> ModelInfo:
        model = self._manager.get_model(self.model_alias)
        if download and not bool(getattr(model, "is_cached", False)):
            model.download()
        return self._manager.get_model_info(self.model_alias)

    def load(self) -> None:
        try:
            self._model = self._manager.get_model(self.model_alias)
            self._model.load()
            self._client = self._model.get_embedding_client()
        except Exception as exc:
            message = f"Could not load embedding model: {self.model_alias}"
            raise FoundryProviderError(message) from exc

    def embed_one(self, text: str) -> Float32Vector:
        result = self.embed_many([text], batch_size=1)
        return cast(Float32Vector, result.vectors[0])

    def embed_many(self, texts: Sequence[str], *, batch_size: int = 8) -> EmbeddingBatchResult:
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1.")
        if not texts:
            raise ValueError("texts must not be empty.")

        client = self._require_client()
        batches: list[np.ndarray] = []
        try:
            for start in range(0, len(texts), batch_size):
                batch = list(texts[start : start + batch_size])
                response = client.generate_embeddings(batch)
                vectors = [item.embedding for item in response.data]
                batches.append(self._to_float32_matrix(vectors))
        except Exception as exc:
            raise FoundryProviderError("Foundry Local embedding generation failed.") from exc

        matrix = np.vstack(batches).astype(np.float32, copy=False)
        self._validate_matrix(matrix)
        self.dimension = int(matrix.shape[1])
        return EmbeddingBatchResult(
            vectors=matrix,
            model_alias=self.model_alias,
            dimension=self.dimension,
        )

    def unload(self) -> None:
        if self._model is None:
            return
        try:
            self._model.unload()
        except Exception as exc:
            message = f"Could not unload embedding model: {self.model_alias}"
            raise FoundryProviderError(message) from exc
        finally:
            self._client = None
            self._model = None

    def _require_client(self) -> Any:
        if self._client is None:
            raise FoundryProviderError("Embedding model is not loaded.")
        return self._client

    @staticmethod
    def _to_float32_matrix(vectors: Sequence[Sequence[float]]) -> np.ndarray:
        matrix = np.asarray(vectors, dtype=np.float32)
        if matrix.ndim != 2:
            raise ValueError("Embedding response must be a 2D matrix.")
        return matrix

    @staticmethod
    def _validate_matrix(matrix: np.ndarray) -> None:
        if not np.all(np.isfinite(matrix)):
            raise ValueError("Embedding response contains non-finite values.")
