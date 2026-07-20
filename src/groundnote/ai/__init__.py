"""AI provider interfaces and implementations for GroundNote."""

from groundnote.ai.errors import (
    FoundryCatalogError,
    FoundryLocalError,
    FoundryModelUnavailableError,
    FoundryProviderError,
)
from groundnote.ai.interfaces import ChatProvider, EmbeddingProvider
from groundnote.ai.models import (
    ChatGenerationRequest,
    ChatGenerationResult,
    ChatMessage,
    ChatResult,
    EmbeddingBatchResult,
    ModelInfo,
)

__all__ = [
    "ChatGenerationRequest",
    "ChatGenerationResult",
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
