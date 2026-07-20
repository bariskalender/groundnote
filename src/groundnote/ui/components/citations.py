"""Trusted structured citation rendering."""

from __future__ import annotations

import streamlit as st

from groundnote.rag import Citation
from groundnote.ui.formatting import citation_to_view


def render_citations(citations: list[Citation]) -> None:
    """Render citations in trusted first-use order."""
    if not citations:
        return
    labels = []
    seen: set[tuple[str, int | None, str | None]] = set()
    for citation in citations:
        view = citation_to_view(citation)
        key = (view.label, view.page_number, view.section_title)
        if key in seen:
            continue
        seen.add(key)
        labels.append(f"[{view.citation_id}] {view.label}")
    st.caption("Sources: " + " · ".join(labels))
