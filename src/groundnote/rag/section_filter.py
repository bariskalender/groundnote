"""Section-title aware filtering for retrieved chunks."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from groundnote.retrieval.models import RetrievalResult

_SECTION_STOPWORDS = {
    "a",
    "an",
    "and",
    "answer",
    "belge",
    "bolum",
    "cevap",
    "chapter",
    "document",
    "game",
    "ile",
    "item",
    "model",
    "nedir",
    "nasil",
    "ne",
    "oyun",
    "oyuna",
    "oyunda",
    "oyunu",
    "section",
    "the",
    "ve",
}
_COMPARISON_MARKERS = {
    "compare",
    "comparison",
    "fark",
    "farklari",
    "farkları",
    "karsilastir",
    "karşılaştır",
    "karşılaştırma",
    "versus",
    "vs",
}


@dataclass(frozen=True)
class SectionFilterResult:
    """Filtered retrieval results and safe diagnostic warning labels."""

    results: list[RetrievalResult]
    warnings: list[str]


def filter_results_for_explicit_sections(
    query: str,
    results: list[RetrievalResult],
) -> SectionFilterResult:
    """Prefer chunks from explicitly requested section titles.

    The filter is intentionally conservative. It activates only when the query contains enough
    terms from one or more retrieved section titles. When it cannot identify a unique requested
    section, it leaves ranking unchanged instead of guessing.
    """
    if not results:
        return SectionFilterResult(results=[], warnings=[])

    query_terms = _tokens(query)
    if not query_terms:
        return SectionFilterResult(results=results, warnings=[])

    title_map: dict[str, set[str]] = {}
    for result in results:
        title = _canonical_title(result.section_title)
        if not title or title in title_map:
            continue
        title_terms = _title_terms(title)
        if title_terms:
            title_map[title] = title_terms
    if not title_map:
        return SectionFilterResult(results=results, warnings=[])

    full_matches = {
        title for title, title_terms in title_map.items() if title_terms.issubset(query_terms)
    }
    partial_matches = {
        title
        for title, title_terms in title_map.items()
        if title not in full_matches and _is_partial_title_match(title_terms, query_terms)
    }
    matched_titles = full_matches or partial_matches
    if not matched_titles:
        return SectionFilterResult(results=results, warnings=[])

    if len(matched_titles) > 1 and not _looks_like_comparison(query_terms):
        return SectionFilterResult(results=results, warnings=["section_title_match_ambiguous"])

    filtered = [result for result in results if _result_matches_titles(result, matched_titles)]
    if not filtered:
        return SectionFilterResult(results=results, warnings=[])
    if len(filtered) == len(results):
        return SectionFilterResult(results=results, warnings=["section_title_filter_applied"])
    return SectionFilterResult(
        results=filtered,
        warnings=["section_title_filter_applied", "conflicting_section_chunks_dropped"],
    )


def _result_matches_titles(result: RetrievalResult, matched_titles: set[str]) -> bool:
    title = _canonical_title(result.section_title)
    if title in matched_titles:
        return True
    content = _normalize(result.content)
    return any(title and title in content for title in matched_titles)


def _canonical_title(title: str | None) -> str:
    if not title:
        return ""
    return " ".join(_tokens(title))


def _title_terms(title: str) -> set[str]:
    return {term for term in _tokens(title) if len(term) >= 3 and term not in _SECTION_STOPWORDS}


def _is_partial_title_match(title_terms: set[str], query_terms: set[str]) -> bool:
    overlap = title_terms & query_terms
    if not overlap:
        return False
    if len(title_terms) == 1:
        return len(next(iter(overlap), "")) >= 5
    return len(overlap) >= max(1, len(title_terms) - 1)


def _looks_like_comparison(query_terms: set[str]) -> bool:
    return bool(query_terms & _COMPARISON_MARKERS)


def _tokens(text: str) -> set[str]:
    normalized = _normalize(text)
    return {
        token
        for token in re.findall(r"[a-z0-9.+-]+", normalized, flags=re.IGNORECASE)
        if token and token not in _SECTION_STOPWORDS
    }


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    folded = "".join(character for character in decomposed if not unicodedata.combining(character))
    return (
        folded.replace("ı", "i")
        .replace("đ", "d")
        .replace("ð", "d")
        .replace("ş", "s")
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ö", "o")
        .replace("ç", "c")
    )
