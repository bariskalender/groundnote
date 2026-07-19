from __future__ import annotations

from groundnote.chunking.sentence_splitter import split_sentences


def test_sentence_splitter_preserves_decimals_and_common_abbreviations() -> None:
    text = "Dr. Ada measured 3.14 units. This is complete! Bu doğru mu?"

    sentences = split_sentences(text)

    assert sentences == [
        "Dr. Ada measured 3.14 units.",
        "This is complete!",
        "Bu doğru mu?",
    ]


def test_sentence_splitter_preserves_math_and_urls_reasonably() -> None:
    text = "Use E = mc^2. Visit https://example.com/test before class."

    sentences = split_sentences(text)

    assert "Use E = mc^2." in sentences
    assert sentences[-1] == "Visit https://example.com/test before class."
