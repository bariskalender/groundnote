"""Text separator helpers for hybrid recursive chunking."""

from __future__ import annotations

import re

_CODE_FENCE_RE = re.compile(r"(```.*?```)", re.DOTALL)


def split_paragraphs_preserving_code(text: str) -> list[str]:
    """Split on blank lines while keeping fenced code blocks as coherent units."""
    parts: list[str] = []
    for block_index, block in enumerate(_CODE_FENCE_RE.split(text.strip())):
        if not block.strip():
            continue
        if block_index % 2 == 1:
            parts.append(block.strip())
            continue
        parts.extend(
            paragraph.strip() for paragraph in re.split(r"\n\s*\n+", block) if paragraph.strip()
        )
    return parts


def split_whitespace_units(text: str) -> list[str]:
    """Return whitespace-delimited units while preserving all non-whitespace text."""
    return re.findall(r"\S+", text)


def join_units(units: list[str]) -> str:
    """Join split text units with single spaces."""
    return " ".join(unit for unit in units if unit)
