"""Lightweight deterministic query routing for chat UX."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from groundnote.rag.language import resolve_response_language


class QueryIntent(StrEnum):
    """Supported deterministic query intents."""

    GREETING = "greeting"
    THANKS = "thanks"
    APP_HELP = "app_help"
    DOCUMENT_QUESTION = "document_question"


@dataclass(frozen=True)
class RoutedQuery:
    """Intent classification without exposing private content."""

    intent: QueryIntent
    language: str


_GREETING = {
    "hello",
    "hi",
    "hey",
    "merhaba",
    "selam",
    "nasilsin",
    "nasılsın",
    "günaydın",
    "iyi akşamlar",
}
_THANKS = {
    "thanks",
    "thank you",
    "teşekkürler",
    "tesekkurler",
    "teşekkür ederim",
    "sağ ol",
    "sag ol",
}
_APP_HELP = {
    "what can you do",
    "which files do you support",
    "how do i upload a document",
    "hangi dosyaları destekliyorsun",
    "nasil belge yuklerim",
    "nasıl belge yüklerim",
    "ne yapabilirsin",
}


def route_query(text: str, *, response_language: str | None = None) -> RoutedQuery:
    """Classify simple app-level messages before local model work."""
    normalized = _normalize(text)
    language = resolve_response_language(text, response_language)
    if normalized in _GREETING or _contains_any(normalized, _GREETING):
        return RoutedQuery(intent=QueryIntent.GREETING, language=language)
    if normalized in _THANKS or _contains_any(normalized, _THANKS):
        return RoutedQuery(intent=QueryIntent.THANKS, language=language)
    if normalized in _APP_HELP or _contains_any(normalized, _APP_HELP):
        return RoutedQuery(intent=QueryIntent.APP_HELP, language=language)
    return RoutedQuery(intent=QueryIntent.DOCUMENT_QUESTION, language=language)


def deterministic_response(intent: QueryIntent, *, language: str) -> str:
    """Return localized deterministic text for non-RAG intents."""
    if language == "tr":
        if intent is QueryIntent.GREETING:
            return "Merhaba, iyiyim. Belgelerin hakkında soru sormaya hazırım."
        if intent is QueryIntent.THANKS:
            return "Rica ederim. Belgelerinle ilgili başka bir soruya hazırım."
        return (
            "PDF, DOCX, TXT ve Markdown belgelerini yerel olarak indeksleyebilirim. "
            "Belgelerini kenar çubuğundan yükleyip sonra içerikleri hakkında soru sorabilirsin."
        )
    if intent is QueryIntent.GREETING:
        return "Hi, I am ready to help with your indexed documents."
    if intent is QueryIntent.THANKS:
        return "You are welcome. Ask another document question whenever you are ready."
    return (
        "I can locally index PDF, DOCX, TXT, and Markdown files. "
        "Upload documents from the sidebar, then ask questions about their contents."
    )


def _normalize(text: str) -> str:
    return " ".join(text.casefold().strip().split())


def _contains_any(text: str, phrases: set[str]) -> bool:
    return any(phrase in text for phrase in phrases if len(phrase) >= 5)
