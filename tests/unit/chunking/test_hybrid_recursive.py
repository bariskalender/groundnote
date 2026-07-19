from __future__ import annotations

import pytest
from pydantic import ValidationError

from groundnote.chunking import ChunkingSettings, HybridRecursiveChunker
from groundnote.documents import ParsedDocument, ParsedSection
from groundnote.domain import SupportedFileType


def test_chunking_settings_validate_defaults_and_relationships() -> None:
    defaults = ChunkingSettings()

    assert defaults.target_characters == 900
    assert defaults.maximum_characters == 1400
    assert defaults.overlap_characters == 120
    assert defaults.minimum_characters == 120
    assert defaults.version == "hybrid-recursive-v1"

    with pytest.raises(ValidationError):
        ChunkingSettings(target_characters=0)
    with pytest.raises(ValidationError):
        ChunkingSettings(target_characters=100, maximum_characters=99)
    with pytest.raises(ValidationError):
        ChunkingSettings(target_characters=100, overlap_characters=100)
    with pytest.raises(ValidationError):
        ChunkingSettings(target_characters=100, minimum_characters=101)


def test_paragraphs_combine_until_target_and_preserve_order() -> None:
    document = _document(
        [
            ParsedSection(
                text="Alpha paragraph.\n\nBeta paragraph.\n\nGamma paragraph.",
                page_number=1,
                section_title="Intro",
                source_order=0,
            )
        ]
    )

    result = HybridRecursiveChunker().chunk(
        document,
        ChunkingSettings(
            target_characters=80,
            maximum_characters=120,
            overlap_characters=0,
            minimum_characters=10,
        ),
    )

    assert result.chunk_count == 1
    assert result.chunks[0].content == "Alpha paragraph.\n\nBeta paragraph.\n\nGamma paragraph."
    assert result.chunks[0].source_start_order == 0
    assert result.chunks[0].source_end_order == 0


def test_long_paragraph_splits_by_sentence_and_preserves_turkish_math() -> None:
    text = (
        "Birinci cümle çok önemlidir. "
        "İkinci cümlede ∑ ve x^2 sembolleri kalır. "
        "Third sentence ends cleanly."
    )
    result = HybridRecursiveChunker().chunk(
        _document([ParsedSection(text=text, source_order=0)]),
        ChunkingSettings(
            target_characters=45,
            maximum_characters=65,
            overlap_characters=0,
            minimum_characters=10,
        ),
    )

    assert result.chunk_count >= 2
    assert all(chunk.character_count <= 65 for chunk in result.chunks)
    joined = " ".join(chunk.content for chunk in result.chunks)
    assert "İkinci" in joined
    assert "∑" in joined
    assert "x^2" in joined


def test_whitespace_and_hard_fallback_do_not_lose_characters() -> None:
    long_token = "x" * 95
    text = f"alpha beta {long_token}"
    result = HybridRecursiveChunker().chunk(
        _document([ParsedSection(text=text, source_order=0)]),
        ChunkingSettings(
            target_characters=30,
            maximum_characters=40,
            overlap_characters=0,
            minimum_characters=1,
        ),
    )

    combined = "".join(chunk.content.replace(" ", "") for chunk in result.chunks)

    assert combined == text.replace(" ", "")
    assert any(
        "hard_split_used_for_long_unbroken_text" in chunk.warnings for chunk in result.chunks
    )


def test_overlap_applies_only_within_page_and_section() -> None:
    first_text = "First page sentence one. First page sentence two. First page sentence three."
    second_text = "Second page sentence one. Second page sentence two."
    document = _document(
        [
            ParsedSection(text=first_text, page_number=1, section_title="A", source_order=0),
            ParsedSection(text=second_text, page_number=2, section_title="A", source_order=1),
        ]
    )

    result = HybridRecursiveChunker().chunk(
        document,
        ChunkingSettings(
            target_characters=35,
            maximum_characters=70,
            overlap_characters=20,
            minimum_characters=5,
        ),
    )

    page_two_chunks = [chunk for chunk in result.chunks if chunk.page_number == 2]

    assert page_two_chunks
    assert page_two_chunks[0].content.startswith("Second page")
    assert all(chunk.character_count <= 70 for chunk in result.chunks)


def test_short_fragments_merge_safely_and_warn_when_boundary_prevents_merge() -> None:
    document = _document(
        [
            ParsedSection(text="Tiny", page_number=1, section_title="A", source_order=0),
            ParsedSection(
                text="Useful continuation text.",
                page_number=1,
                section_title="A",
                source_order=1,
            ),
            ParsedSection(text="End", page_number=2, section_title="A", source_order=2),
        ]
    )

    result = HybridRecursiveChunker().chunk(
        document,
        ChunkingSettings(
            target_characters=60,
            maximum_characters=80,
            overlap_characters=0,
            minimum_characters=10,
        ),
    )

    assert result.chunks[0].content.startswith("Tiny")
    assert result.chunks[-1].page_number == 2
    assert "undersized_chunk_kept_to_preserve_boundaries" in result.chunks[-1].warnings


def test_metadata_indexes_counts_and_determinism() -> None:
    document = _document(
        [
            ParsedSection(
                text="# Heading\n\nContent A. Content B.",
                section_title="Heading",
                source_order=0,
            ),
            ParsedSection(text="Another section.", section_title="Next", source_order=1),
        ],
        file_type=SupportedFileType.MARKDOWN,
    )
    settings = ChunkingSettings(
        target_characters=35,
        maximum_characters=70,
        overlap_characters=0,
        minimum_characters=5,
    )
    first = HybridRecursiveChunker().chunk(document, settings)
    second = HybridRecursiveChunker().chunk(document, settings)

    assert [chunk.content for chunk in first.chunks] == [chunk.content for chunk in second.chunks]
    assert [chunk.model_dump(exclude={"document_id"}) for chunk in first.chunks] == [
        chunk.model_dump(exclude={"document_id"}) for chunk in second.chunks
    ]
    assert [chunk.chunk_index for chunk in first.chunks] == list(range(first.chunk_count))
    assert all(chunk.character_count == len(chunk.content) for chunk in first.chunks)
    assert all(chunk.token_estimate is not None for chunk in first.chunks)
    assert first.chunks[0].section_title == "Heading"
    assert first.chunks[0].chunking_version == "hybrid-recursive-v1"


def test_code_block_remains_usable_and_null_bytes_are_removed() -> None:
    text = "Intro.\n\n```python\nprint('merhaba')\n```\n\nTail\x00 text."
    result = HybridRecursiveChunker().chunk(
        _document([ParsedSection(text=text, source_order=0)]),
        ChunkingSettings(
            target_characters=120,
            maximum_characters=160,
            overlap_characters=0,
            minimum_characters=5,
        ),
    )

    content = result.chunks[0].content

    assert "```python" in content
    assert "print('merhaba')" in content
    assert "\x00" not in content


def _document(
    sections: list[ParsedSection],
    *,
    file_type: SupportedFileType = SupportedFileType.TXT,
) -> ParsedDocument:
    return ParsedDocument(
        original_filename="notes.txt",
        stored_filename="safe-notes.txt",
        file_type=file_type,
        sha256="a" * 64,
        file_size_bytes=100,
        page_count=2 if file_type == SupportedFileType.PDF else None,
        sections=sections,
    )
