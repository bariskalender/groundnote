"""Trusted structured citation rendering."""

from __future__ import annotations

import streamlit as st

from groundnote.rag import Citation
from groundnote.ui.formatting import citation_to_view


def render_citations(citations: list[Citation]) -> None:
    """Render citations in trusted first-use order."""
    if not citations:
        return
    with st.expander(f"Sources ({len(citations)})", expanded=True):
        for citation in citations:
            view = citation_to_view(citation)
            st.markdown(f"**[{view.citation_id}]** {view.label}")
            with st.expander(f"Technical details for {view.citation_id}", expanded=False):
                st.write(f"File type: {view.file_type}")
                if view.score is not None:
                    st.write(f"Retrieval score: {view.score:.3f}")
