"""Lightweight English and Turkish sentence splitting heuristics."""

from __future__ import annotations

import re

_ABBREVIATIONS = {
    "dr",
    "mr",
    "mrs",
    "ms",
    "prof",
    "sr",
    "jr",
    "e.g",
    "i.e",
    "vs",
    "etc",
    "bkz",
    "örn",
    "sn",
}


def split_sentences(text: str) -> list[str]:
    """Split text on common sentence endings without heavy NLP dependencies."""
    normalized = text.strip()
    if not normalized:
        return []

    parts: list[str] = []
    start = 0
    for index, character in enumerate(normalized):
        if character not in ".!?":
            continue
        if _is_decimal_point(normalized, index) or _is_abbreviation(normalized, index):
            continue
        next_index = index + 1
        if next_index < len(normalized) and not normalized[next_index].isspace():
            continue
        segment = normalized[start:next_index].strip()
        if segment:
            parts.append(segment)
        start = next_index

    tail = normalized[start:].strip()
    if tail:
        parts.append(tail)
    return parts or [normalized]


def _is_decimal_point(text: str, index: int) -> bool:
    return (
        text[index] == "."
        and index > 0
        and index + 1 < len(text)
        and text[index - 1].isdigit()
        and text[index + 1].isdigit()
    )


def _is_abbreviation(text: str, index: int) -> bool:
    if text[index] != ".":
        return False
    prefix = text[:index].rstrip()
    match = re.search(r"([A-Za-zÇĞİÖŞÜçğıöşü.]+)$", prefix)
    if match is None:
        return False
    return match.group(1).lower() in _ABBREVIATIONS
