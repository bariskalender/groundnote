"""Chunking service factories and mapping helpers."""

from __future__ import annotations

import json
import uuid
from typing import Any

from groundnote.chunking.models import ChunkingSettings, TextChunk
from groundnote.config import Settings
from groundnote.domain import DocumentChunk


def settings_to_chunking_settings(settings: Settings) -> ChunkingSettings:
    """Create validated chunking settings from application settings."""
    return ChunkingSettings(
        target_characters=settings.chunk_target_characters,
        maximum_characters=settings.chunk_maximum_characters,
        overlap_characters=settings.chunk_overlap_characters,
        minimum_characters=settings.chunk_minimum_characters,
        version=settings.chunking_version,
    )


def estimate_tokens(text: str) -> int:
    """Estimate tokens with a coarse character-count heuristic."""
    return max(1, round(len(text) / 4))


def text_chunk_to_document_chunk(chunk: TextChunk, *, document_id: str) -> DocumentChunk:
    """Map a pre-embedding text chunk to the persistence domain model."""
    return DocumentChunk(
        id=str(uuid.uuid4()),
        document_id=document_id,
        chunk_index=chunk.chunk_index,
        content=chunk.content,
        page_number=chunk.page_number,
        section_title=chunk.section_title,
        character_count=chunk.character_count,
        token_estimate=chunk.token_estimate,
        embedding_dimension=None,
        source_start_order=chunk.source_start_order,
        source_end_order=chunk.source_end_order,
        chunking_version=chunk.chunking_version,
        metadata_json=_safe_metadata_json(chunk.metadata),
    )


def _safe_metadata_json(metadata: dict[str, Any]) -> str:
    return json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
