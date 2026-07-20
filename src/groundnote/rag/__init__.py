"""Grounded single-turn RAG generation."""

from groundnote.rag.errors import (
    ChatGenerationError,
    ChatModelLoadError,
    ChatProviderUnavailableError,
    CitationValidationError,
    ContextAssemblyError,
    EmptyRagQueryError,
    InvalidChatResponseError,
    NoRelevantContextError,
    PromptConstructionError,
    RagError,
    RagRetrievalError,
    RepeatingGenerationError,
    UnsupportedResponseLanguageError,
)
from groundnote.rag.models import Citation, RagAnswer, RagContextItem, RagRequest, RagResponse
from groundnote.rag.router import QueryIntent, RoutedQuery, deterministic_response, route_query
from groundnote.rag.service import RagService, safe_performance_report

__all__ = [
    "ChatGenerationError",
    "ChatModelLoadError",
    "ChatProviderUnavailableError",
    "Citation",
    "CitationValidationError",
    "ContextAssemblyError",
    "EmptyRagQueryError",
    "InvalidChatResponseError",
    "NoRelevantContextError",
    "PromptConstructionError",
    "QueryIntent",
    "RagAnswer",
    "RagContextItem",
    "RagError",
    "RagRequest",
    "RagResponse",
    "RagRetrievalError",
    "RagService",
    "RepeatingGenerationError",
    "RoutedQuery",
    "UnsupportedResponseLanguageError",
    "deterministic_response",
    "route_query",
    "safe_performance_report",
]
