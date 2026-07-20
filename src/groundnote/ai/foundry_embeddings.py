"""Foundry Local embedding provider."""

from __future__ import annotations

import re
import shutil
import subprocess
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
        self._local_service_client: Any | None = None
        self._local_service_model_id: str | None = None

    def ensure_model_available(self, *, download: bool = False) -> ModelInfo:
        model = self._manager.get_model(self.model_alias)
        if download and not bool(getattr(model, "is_cached", False)):
            model.download()
        return self._manager.get_model_info(self.model_alias)

    def load(self) -> None:
        if self._client is not None or self._local_service_client is not None:
            return
        try:
            self._model = self._manager.get_model(self.model_alias)
            self._model.load()
            self._client = self._model.get_embedding_client()
        except Exception:
            try:
                self._load_via_local_service()
            except Exception as fallback_exc:
                message = f"Could not load embedding model: {self.model_alias}"
                raise FoundryProviderError(message) from fallback_exc

    def embed_one(self, text: str) -> Float32Vector:
        result = self.embed_many([text], batch_size=1)
        return cast(Float32Vector, result.vectors[0])

    def embed_many(self, texts: Sequence[str], *, batch_size: int = 8) -> EmbeddingBatchResult:
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1.")
        if not texts:
            raise ValueError("texts must not be empty.")

        batches: list[np.ndarray] = []
        try:
            for start in range(0, len(texts), batch_size):
                batch = list(texts[start : start + batch_size])
                vectors = self._generate_embeddings(batch)
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
        if self._local_service_model_id is not None:
            self._unload_local_service_model()
            self._local_service_client = None
            self._local_service_model_id = None
            self._client = None
            self._model = None
            return
        if self._model is not None:
            try:
                self._model.unload()
            except Exception as exc:
                message = f"Could not unload embedding model: {self.model_alias}"
                raise FoundryProviderError(message) from exc
            finally:
                self._client = None
                self._model = None

    def _generate_embeddings(self, batch: list[str]) -> Sequence[Sequence[float]]:
        if self._local_service_client is not None:
            if self._local_service_model_id is None:
                raise FoundryProviderError("Local Foundry service model is not loaded.")
            response = self._local_service_client.embeddings.create(
                model=self._local_service_model_id,
                input=batch,
            )
            return [item.embedding for item in response.data]
        client = self._require_client()
        response = client.generate_embeddings(batch)
        return [item.embedding for item in response.data]

    def _require_client(self) -> Any:
        if self._client is None:
            raise FoundryProviderError("Embedding model is not loaded.")
        return self._client

    def _load_via_local_service(self) -> None:
        """Use the local OpenAI-compatible Foundry daemon when direct SDK load is unavailable."""
        model_id = self._model_id()
        self._run_foundry(["model", "load", model_id], timeout_seconds=120)
        base_url = self._local_service_base_url()
        from openai import OpenAI

        self._local_service_client = OpenAI(base_url=f"{base_url}/v1", api_key="local-foundry")
        self._local_service_model_id = model_id
        self._client = None

    def _unload_local_service_model(self) -> None:
        if self._local_service_model_id is None:
            return
        self._run_foundry(
            ["model", "unload", self._local_service_model_id],
            timeout_seconds=120,
            check=False,
        )

    def _model_id(self) -> str:
        model = self._model or self._manager.get_model(self.model_alias)
        model_id = str(getattr(model, "id", "")).strip()
        if not model_id:
            raise FoundryProviderError("Foundry Local model id is unavailable.")
        return model_id

    @classmethod
    def _local_service_base_url(cls) -> str:
        completed = cls._run_foundry(["server", "status"], timeout_seconds=30)
        match = re.search(r"http://127\.0\.0\.1:\d+", completed.stdout)
        if match is None:
            raise FoundryProviderError("Foundry Local service URL is unavailable.")
        return match.group(0)

    @staticmethod
    def _run_foundry(
        arguments: list[str],
        *,
        timeout_seconds: int,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        foundry_path = shutil.which("foundry")
        if foundry_path is None:
            raise FoundryProviderError("Foundry Local CLI is not available.")
        completed = subprocess.run(
            [foundry_path, *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        if check and completed.returncode != 0:
            raise FoundryProviderError("Foundry Local CLI command failed.")
        return completed

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
