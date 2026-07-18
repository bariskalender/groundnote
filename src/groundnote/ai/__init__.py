"""AI provider interfaces and implementations for GroundNote."""

from groundnote.ai.errors import (
    FoundryCatalogError,
    FoundryLocalError,
    FoundryModelUnavailableError,
    FoundryProviderError,
)
from groundnote.ai.interfaces import ChatProvider, EmbeddingProvider
from groundnote.ai.models import ChatMessage, ChatResult, EmbeddingBatchResult, ModelInfo

__all__ = [
    "ChatMessage",
    "ChatProvider",
    "ChatResult",
    "EmbeddingBatchResult",
    "EmbeddingProvider",
    "FoundryCatalogError",
    "FoundryLocalError",
    "FoundryModelUnavailableError",
    "FoundryProviderError",
    "ModelInfo",
]
