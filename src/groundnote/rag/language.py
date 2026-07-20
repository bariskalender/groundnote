"""Lightweight deterministic response-language selection."""

from __future__ import annotations

from groundnote.rag.errors import UnsupportedResponseLanguageError

SUPPORTED_LANGUAGES = {"tr", "en", "auto"}
TURKISH_CHARS = set("çğıöşüÇĞİÖŞÜ")
TURKISH_MARKERS = {
    "ve",
    "bir",
    "bu",
    "şu",
    "nedir",
    "nasıl",
    "nerede",
    "hangi",
    "için",
    "ile",
    "değil",
    "belgeleri",
}
ENGLISH_MARKERS = {
    "the",
    "and",
    "what",
    "where",
    "how",
    "why",
    "is",
    "are",
    "does",
    "store",
    "explain",
}


def resolve_response_language(query: str, explicit: str | None) -> str:
    """Return `tr` or `en` using explicit override or a lightweight heuristic."""
    requested = (explicit or "auto").strip().lower()
    if requested not in SUPPORTED_LANGUAGES:
        raise UnsupportedResponseLanguageError("Unsupported response language.")
    if requested in {"tr", "en"}:
        return requested
    return infer_language(query)


def infer_language(query: str) -> str:
    """Infer Turkish or English conservatively; uncertain input defaults to English."""
    if any(char in TURKISH_CHARS for char in query):
        return "tr"
    words = {word.strip(".,?!:;()[]{}\"'`").lower() for word in query.split()}
    turkish_score = len(words & TURKISH_MARKERS)
    english_score = len(words & ENGLISH_MARKERS)
    if turkish_score > english_score:
        return "tr"
    return "en"
