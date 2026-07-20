"""RAG-specific user-safe errors."""

from __future__ import annotations


class RagError(RuntimeError):
    """Base error for grounded RAG generation failures."""


class EmptyRagQueryError(RagError):
    """Raised when a RAG query is empty."""


class RagRetrievalError(RagError):
    """Raised when semantic retrieval fails during RAG."""


class NoRelevantContextError(RagError):
    """Raised when no usable retrieved context is available."""


class ContextAssemblyError(RagError):
    """Raised when retrieved chunks cannot be assembled safely."""


class PromptConstructionError(RagError):
    """Raised when prompts cannot be constructed safely."""


class ChatProviderUnavailableError(RagError):
    """Raised when the local chat provider cannot be used."""


class ChatModelLoadError(RagError):
    """Raised when the local chat model cannot be loaded."""


class ChatGenerationError(RagError):
    """Raised when local chat generation fails."""


class InvalidChatResponseError(RagError):
    """Raised when generated chat output is unsafe or malformed."""


class CitationValidationError(RagError):
    """Raised when generated citations cannot be validated."""


class UnsupportedResponseLanguageError(RagError):
    """Raised when the requested response language is unsupported."""
