"""Deterministic hybrid recursive chunker."""

from __future__ import annotations

from dataclasses import dataclass, field

from groundnote.chunking.errors import (
    ChunkMetadataError,
    ChunkSizeError,
    EmptyChunkError,
    InvalidChunkSettingsError,
)
from groundnote.chunking.models import ChunkingResult, ChunkingSettings, TextChunk
from groundnote.chunking.sentence_splitter import split_sentences
from groundnote.chunking.separators import (
    join_units,
    split_paragraphs_preserving_code,
    split_whitespace_units,
)
from groundnote.chunking.service import estimate_tokens
from groundnote.documents import ParsedDocument, ParsedSection


@dataclass
class _Unit:
    text: str
    page_number: int | None
    section_title: str | None
    source_start_order: int
    source_end_order: int
    source_section_index: int
    warnings: list[str] = field(default_factory=list)

    def compatible_with(self, other: _Unit) -> bool:
        return self.page_number == other.page_number and self.section_title == other.section_title


class HybridRecursiveChunker:
    """Split parsed documents into deterministic, metadata-rich text chunks."""

    def chunk(
        self,
        document: ParsedDocument,
        settings: ChunkingSettings,
    ) -> ChunkingResult:
        """Chunk a parsed document without model calls or embeddings."""
        _validate_settings(settings)
        sections = sorted(document.sections, key=lambda item: item.source_order)
        units = self._sections_to_units(sections, settings)
        packed = self._pack_units(units, settings)
        merged = self._merge_short_fragments(packed, settings)
        overlapped = self._apply_overlap(merged, settings)
        chunks = [
            _unit_to_chunk(
                unit,
                index=index,
                document=document,
                version=settings.version,
            )
            for index, unit in enumerate(overlapped)
        ]
        _validate_chunks(chunks, settings)
        warnings = [warning for chunk in chunks for warning in chunk.warnings]
        warnings.extend(document.warnings)
        return ChunkingResult(
            chunks=chunks,
            warnings=warnings,
            original_section_count=len(sections),
            chunk_count=len(chunks),
            total_character_count=sum(chunk.character_count for chunk in chunks),
            chunking_version=settings.version,
        )

    def _sections_to_units(
        self,
        sections: list[ParsedSection],
        settings: ChunkingSettings,
    ) -> list[_Unit]:
        units: list[_Unit] = []
        for section_index, section in enumerate(sections):
            paragraphs = split_paragraphs_preserving_code(section.text)
            for paragraph in paragraphs:
                units.extend(
                    self._split_oversized_text(paragraph, section, section_index, settings)
                )
        return units

    def _split_oversized_text(
        self,
        text: str,
        section: ParsedSection,
        section_index: int,
        settings: ChunkingSettings,
    ) -> list[_Unit]:
        cleaned = text.replace("\x00", "").strip()
        if not cleaned:
            return []
        if len(cleaned) <= settings.maximum_characters:
            return [_unit_from_section(cleaned, section, section_index)]

        sentence_units = split_sentences(cleaned)
        if len(sentence_units) > 1:
            return self._pack_text_units(sentence_units, section, section_index, settings)

        whitespace_units = split_whitespace_units(cleaned)
        if len(whitespace_units) > 1:
            return self._pack_text_units(whitespace_units, section, section_index, settings)

        return self._hard_split(cleaned, section, section_index, settings)

    def _pack_text_units(
        self,
        text_units: list[str],
        section: ParsedSection,
        section_index: int,
        settings: ChunkingSettings,
    ) -> list[_Unit]:
        packed: list[_Unit] = []
        current: list[str] = []
        for text_unit in text_units:
            if len(text_unit) > settings.maximum_characters:
                if current:
                    packed.append(_unit_from_section(join_units(current), section, section_index))
                    current = []
                packed.extend(self._hard_split(text_unit, section, section_index, settings))
                continue
            candidate = join_units([*current, text_unit])
            if current and len(candidate) > settings.maximum_characters:
                packed.append(_unit_from_section(join_units(current), section, section_index))
                current = [text_unit]
            else:
                current.append(text_unit)
            if len(join_units(current)) >= settings.target_characters:
                packed.append(_unit_from_section(join_units(current), section, section_index))
                current = []
        if current:
            packed.append(_unit_from_section(join_units(current), section, section_index))
        return packed

    def _hard_split(
        self,
        text: str,
        section: ParsedSection,
        section_index: int,
        settings: ChunkingSettings,
    ) -> list[_Unit]:
        units: list[_Unit] = []
        for start in range(0, len(text), settings.maximum_characters):
            segment = text[start : start + settings.maximum_characters]
            if segment:
                unit = _unit_from_section(segment, section, section_index)
                unit.warnings.append("hard_split_used_for_long_unbroken_text")
                units.append(unit)
        return units

    def _pack_units(self, units: list[_Unit], settings: ChunkingSettings) -> list[_Unit]:
        packed: list[_Unit] = []
        current: _Unit | None = None
        for unit in units:
            if current is None:
                current = unit
                continue
            combined_text = _join_chunk_text([current.text, unit.text])
            can_merge = (
                current.compatible_with(unit) and len(combined_text) <= settings.maximum_characters
            )
            should_merge = can_merge and len(combined_text) <= settings.target_characters
            if should_merge:
                current = _merge_units(current, unit, combined_text)
            else:
                packed.append(current)
                current = unit
        if current is not None:
            packed.append(current)
        return packed

    def _merge_short_fragments(
        self,
        units: list[_Unit],
        settings: ChunkingSettings,
    ) -> list[_Unit]:
        if not units:
            return []
        result: list[_Unit] = []
        index = 0
        while index < len(units):
            unit = units[index]
            if len(unit.text) >= settings.minimum_characters:
                result.append(unit)
                index += 1
                continue
            if result and _can_merge(result[-1], unit, settings):
                result[-1] = _merge_units(
                    result[-1],
                    unit,
                    _join_chunk_text([result[-1].text, unit.text]),
                )
                index += 1
                continue
            if index + 1 < len(units) and _can_merge(unit, units[index + 1], settings):
                next_unit = units[index + 1]
                merged = _merge_units(
                    unit,
                    next_unit,
                    _join_chunk_text([unit.text, next_unit.text]),
                )
                result.append(merged)
                index += 2
                continue
            unit.warnings.append("undersized_chunk_kept_to_preserve_boundaries")
            result.append(unit)
            index += 1
        return result

    def _apply_overlap(self, units: list[_Unit], settings: ChunkingSettings) -> list[_Unit]:
        if settings.overlap_characters == 0:
            return units
        result: list[_Unit] = []
        previous: _Unit | None = None
        for unit in units:
            current = unit
            if previous is not None and previous.compatible_with(unit):
                prefix = _overlap_prefix(previous.text, settings.overlap_characters)
                if (
                    prefix
                    and prefix != previous.text
                    and not unit.text.startswith(prefix)
                    and len(prefix) + 2 + len(unit.text) <= settings.maximum_characters
                ):
                    current = _Unit(
                        text=_join_chunk_text([prefix, unit.text]),
                        page_number=unit.page_number,
                        section_title=unit.section_title,
                        source_start_order=unit.source_start_order,
                        source_end_order=unit.source_end_order,
                        source_section_index=unit.source_section_index,
                        warnings=[*unit.warnings, "overlap_prefix_added"],
                    )
            result.append(current)
            previous = unit
        return result


def _unit_from_section(text: str, section: ParsedSection, section_index: int) -> _Unit:
    return _Unit(
        text=text,
        page_number=section.page_number,
        section_title=section.section_title,
        source_start_order=section.source_order,
        source_end_order=section.source_order,
        source_section_index=section_index,
        warnings=list(section.warnings),
    )


def _merge_units(left: _Unit, right: _Unit, text: str) -> _Unit:
    return _Unit(
        text=text,
        page_number=left.page_number,
        section_title=left.section_title,
        source_start_order=min(left.source_start_order, right.source_start_order),
        source_end_order=max(left.source_end_order, right.source_end_order),
        source_section_index=min(left.source_section_index, right.source_section_index),
        warnings=[*left.warnings, *right.warnings],
    )


def _can_merge(left: _Unit, right: _Unit, settings: ChunkingSettings) -> bool:
    return (
        left.compatible_with(right)
        and len(_join_chunk_text([left.text, right.text])) <= settings.maximum_characters
    )


def _join_chunk_text(parts: list[str]) -> str:
    return "\n\n".join(part.strip() for part in parts if part.strip())


def _overlap_prefix(text: str, limit: int) -> str:
    if limit <= 0 or not text:
        return ""
    suffix = text[-limit:].strip()
    if not suffix:
        return ""
    for separator in (". ", "! ", "? ", "\n\n", " "):
        position = suffix.find(separator)
        if 0 <= position < len(suffix) - len(separator):
            return suffix[position + len(separator) :].strip()
    return suffix


def _unit_to_chunk(
    unit: _Unit,
    *,
    index: int,
    document: ParsedDocument,
    version: str,
) -> TextChunk:
    content = unit.text.replace("\x00", "").strip()
    metadata = {
        "source_filename": document.original_filename,
        "source_file_type": document.file_type.value,
        "source_start_order": unit.source_start_order,
        "source_end_order": unit.source_end_order,
        "warnings": unit.warnings,
    }
    return TextChunk(
        chunk_index=index,
        content=content,
        page_number=unit.page_number,
        section_title=unit.section_title,
        character_count=len(content),
        token_estimate=estimate_tokens(content),
        source_start_order=unit.source_start_order,
        source_end_order=unit.source_end_order,
        chunking_version=version,
        metadata=metadata,
        warnings=unit.warnings,
    )


def _validate_settings(settings: ChunkingSettings) -> None:
    try:
        ChunkingSettings.model_validate(settings)
    except ValueError as exc:
        raise InvalidChunkSettingsError("Chunking settings are invalid.") from exc


def _validate_chunks(chunks: list[TextChunk], settings: ChunkingSettings) -> None:
    seen_contents: set[str] = set()
    for expected_index, chunk in enumerate(chunks):
        if chunk.chunk_index != expected_index:
            raise ChunkMetadataError("Chunk indexes must be sequential.")
        if not chunk.content.strip():
            raise EmptyChunkError("Chunk content must not be empty.")
        if "\x00" in chunk.content:
            raise ChunkMetadataError("Chunk content contains a null byte.")
        if chunk.character_count != len(chunk.content):
            raise ChunkMetadataError("Chunk character count does not match content length.")
        if chunk.page_number is not None and chunk.page_number <= 0:
            raise ChunkMetadataError("Chunk page number must be positive.")
        if not chunk.chunking_version:
            raise ChunkMetadataError("Chunking version must be present.")
        if chunk.character_count > settings.maximum_characters and not chunk.warnings:
            raise ChunkSizeError("Chunk exceeds maximum size.")
        if chunk.content in seen_contents:
            chunk.warnings.append("duplicate_chunk_content_detected")
        seen_contents.add(chunk.content)
