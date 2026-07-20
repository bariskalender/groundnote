"""Fake AI providers for unit tests."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import cast

import numpy as np

from groundnote.ai.interfaces import Float32Vector
from groundnote.ai.models import (
    ChatGenerationRequest,
    ChatGenerationResult,
    ChatMessage,
    ChatResult,
    EmbeddingBatchResult,
    ModelInfo,
)


class FakeChatProvider:
    """Deterministic chat provider that does not require Foundry Local."""

    def __init__(
        self,
        model_alias: str = "fake-chat",
        responses: Sequence[str] | None = None,
    ) -> None:
        self.model_alias = model_alias
        self.loaded = False
        self.calls = 0
        self.requests: list[ChatGenerationRequest] = []
        self.responses = list(responses or [])

    def ensure_model_available(self, *, download: bool = False) -> ModelInfo:
        return ModelInfo(
            alias=self.model_alias,
            model_id="fake-chat:1",
            task="chat-completion",
            device_type="CPU",
            execution_provider="FakeExecutionProvider",
            file_size_mb=0,
            context_length=1024,
            is_cached=True,
            is_loaded=self.loaded,
        )

    def load(self) -> None:
        self.loaded = True

    def generate(self, messages: Sequence[ChatMessage], *, max_tokens: int = 64) -> ChatResult:
        if not self.loaded:
            raise RuntimeError("Fake chat provider is not loaded.")
        last_user = next(
            (message.content for message in reversed(messages) if message.role == "user"),
            "",
        )
        return ChatResult(
            text=f"fake response: {last_user[:max_tokens]}",
            model_alias=self.model_alias,
        )

    def generate_request(self, request: ChatGenerationRequest) -> ChatGenerationResult:
        if not self.loaded:
            raise RuntimeError("Fake chat provider is not loaded.")
        self.calls += 1
        self.requests.append(request)
        text = self.responses.pop(0) if self.responses else "Fake grounded answer. [S1]"
        return ChatGenerationResult(
            text=text,
            model=request.model,
            duration_ms=1.0,
        )

    def stream(self, messages: Sequence[ChatMessage], *, max_tokens: int = 64) -> Iterable[str]:
        yield self.generate(messages, max_tokens=max_tokens).text

    def unload(self) -> None:
        self.loaded = False


class FakeEmbeddingProvider:
    """Deterministic embedding provider that returns finite float32 vectors."""

    def __init__(self, model_alias: str = "fake-embedding", dimension: int = 4) -> None:
        self.model_alias = model_alias
        self.dimension: int | None = dimension
        self.loaded = False
        self._dimension = dimension

    def ensure_model_available(self, *, download: bool = False) -> ModelInfo:
        return ModelInfo(
            alias=self.model_alias,
            model_id="fake-embedding:1",
            task="embedding",
            device_type="CPU",
            execution_provider="FakeExecutionProvider",
            file_size_mb=0,
            context_length=1024,
            is_cached=True,
            is_loaded=self.loaded,
        )

    def load(self) -> None:
        self.loaded = True

    def embed_one(self, text: str) -> Float32Vector:
        return cast(Float32Vector, self.embed_many([text]).vectors[0])

    def embed_many(self, texts: Sequence[str], *, batch_size: int = 8) -> EmbeddingBatchResult:
        if not self.loaded:
            raise RuntimeError("Fake embedding provider is not loaded.")
        vectors = np.vstack([self._embed_text(text) for text in texts]).astype(np.float32)
        return EmbeddingBatchResult(
            vectors=vectors,
            model_alias=self.model_alias,
            dimension=self._dimension,
        )

    def unload(self) -> None:
        self.loaded = False

    def _embed_text(self, text: str) -> Float32Vector:
        values = np.zeros(self._dimension, dtype=np.float32)
        for index, char in enumerate(text.encode("utf-8")):
            values[index % self._dimension] += float(char) / 255.0
        norm = np.linalg.norm(values)
        if norm > 0:
            values = values / norm
        return values.astype(np.float32, copy=False)
