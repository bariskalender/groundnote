"""Small provider contracts for local chat and embedding backends."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol

import numpy as np
import numpy.typing as npt

from groundnote.ai.models import ChatMessage, ChatResult, EmbeddingBatchResult, ModelInfo

Float32Vector = npt.NDArray[np.float32]
Float32Matrix = npt.NDArray[np.float32]


class ChatProvider(Protocol):
    """Provider contract for local chat generation."""

    model_alias: str

    def ensure_model_available(self, *, download: bool = False) -> ModelInfo:
        """Verify the configured model exists, optionally downloading it."""

    def load(self) -> None:
        """Load the configured model for inference."""

    def generate(self, messages: Sequence[ChatMessage], *, max_tokens: int = 64) -> ChatResult:
        """Generate one non-streaming text response."""

    def stream(self, messages: Sequence[ChatMessage], *, max_tokens: int = 64) -> Iterable[str]:
        """Stream a text response when supported by the backend."""

    def unload(self) -> None:
        """Release provider resources when supported."""


class EmbeddingProvider(Protocol):
    """Provider contract for local embedding generation."""

    model_alias: str
    dimension: int | None

    def ensure_model_available(self, *, download: bool = False) -> ModelInfo:
        """Verify the configured embedding model exists, optionally downloading it."""

    def load(self) -> None:
        """Load the configured embedding model for inference."""

    def embed_one(self, text: str) -> Float32Vector:
        """Embed one text and return a finite float32 vector."""

    def embed_many(self, texts: Sequence[str], *, batch_size: int = 8) -> EmbeddingBatchResult:
        """Embed texts in controlled batches and return finite float32 vectors."""

    def unload(self) -> None:
        """Release provider resources when supported."""
