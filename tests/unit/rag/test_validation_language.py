from __future__ import annotations

import pytest

from groundnote.rag import EmptyRagQueryError, RagError, UnsupportedResponseLanguageError
from groundnote.rag.language import resolve_response_language
from groundnote.rag.validation import normalize_query


def test_query_validation_rejects_empty_whitespace_and_long_text() -> None:
    with pytest.raises(EmptyRagQueryError):
        normalize_query(" \r\n\t ", max_characters=10)
    with pytest.raises(RagError):
        normalize_query("x" * 11, max_characters=10)


def test_query_validation_preserves_unicode_math_and_code() -> None:
    query = "  Türkiye için f(x)=α+β nedir?\r\n`print('ç')`  "

    normalized = normalize_query(query, max_characters=200)

    assert normalized == "Türkiye için f(x)=α+β nedir?\n`print('ç')`"


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("Bu belge ne anlatıyor?", "tr"),
        ("Where does GroundNote store embeddings?", "en"),
        ("Where does GroundNote belgeleri işler?", "tr"),
        ("def f(x): return x + 1", "en"),
        ("What is f(x)=α+β?", "en"),
    ],
)
def test_language_detection(query: str, expected: str) -> None:
    assert resolve_response_language(query, "auto") == expected


def test_explicit_language_override_and_invalid_language() -> None:
    assert resolve_response_language("What is this?", "tr") == "tr"
    assert resolve_response_language("Bu nedir?", "en") == "en"
    with pytest.raises(UnsupportedResponseLanguageError):
        resolve_response_language("Hello", "de")
