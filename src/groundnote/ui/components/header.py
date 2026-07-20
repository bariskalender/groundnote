"""Application header component."""

from __future__ import annotations

import streamlit as st


def render_header() -> None:
    """Render the stable GroundNote heading and purpose."""
    st.title("GroundNote")
    st.subheader("Private, Offline RAG Study Assistant")
    st.write(
        "Upload documents, index them locally, and ask grounded questions with source citations."
    )
