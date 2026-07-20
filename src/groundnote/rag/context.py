"""RAG context selection and formatting."""

from __future__ import annotations

from html import escape

from groundnote.config import Settings
from groundnote.rag.errors import ContextAssemblyError
from groundnote.rag.models import RagContextItem
from groundnote.retrieval.models import RetrievalResult


def select_context(
    results: list[RetrievalResult],
    *,
    settings: Settings,
) -> tuple[list[RagContextItem], list[str]]:
    """Select complete retrieved chunks in retrieval order."""
    selected: list[RagContextItem] = []
    warnings: list[str] = []
    seen_chunk_ids: set[str] = set()
    used_characters = 0
    for result in results:
        if len(selected) >= settings.rag_max_chunk_count:
            break
        content = result.content.strip()
        if not content:
            warnings.append("empty_context_chunk_skipped")
            continue
        if result.chunk_id in seen_chunk_ids:
            warnings.append("duplicate_context_chunk_skipped")
            continue
        would_use = used_characters + len(content)
        if selected and would_use > settings.rag_max_context_characters:
            warnings.append("context_limit_reached")
            break
        if not selected and would_use > settings.rag_max_context_characters:
            hard_limit = settings.rag_max_context_characters * 2
            if len(content) > hard_limit:
                raise ContextAssemblyError(
                    "Top retrieved chunk is too large for local RAG context."
                )
            warnings.append("top_chunk_exceeds_soft_context_limit")
        citation_id = f"S{len(selected) + 1}"
        selected.append(
            RagContextItem(
                citation_id=citation_id,
                document_id=result.document_id,
                chunk_id=result.chunk_id,
                chunk_index=result.chunk_index,
                content=content,
                score=result.score,
                source_filename=result.source_filename,
                source_file_type=result.source_file_type,
                page_number=result.page_number,
                section_title=result.section_title,
                source_start_order=result.source_start_order,
                source_end_order=result.source_end_order,
                metadata=dict(result.metadata),
            )
        )
        seen_chunk_ids.add(result.chunk_id)
        used_characters += len(content)
    return selected, warnings


def format_context(items: list[RagContextItem]) -> str:
    """Format selected context with explicit untrusted-source delimiters."""
    parts = ["<retrieved_context>"]
    for item in items:
        parts.extend(
            [
                f'<source id="{item.citation_id}">',
                "<metadata>",
                f"filename: {escape(item.source_filename)}",
                f"file_type: {item.source_file_type.value}",
                f"page: {item.page_number if item.page_number is not None else ''}",
                f"section: {escape(item.section_title or '')}",
                f"chunk_index: {item.chunk_index}",
                "</metadata>",
                "<content>",
                escape(item.content),
                "</content>",
                "</source>",
            ]
        )
    parts.append("</retrieved_context>")
    return "\n".join(parts)
