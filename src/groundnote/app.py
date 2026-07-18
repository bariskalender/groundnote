"""Minimal Streamlit application shell for GroundNote."""

from __future__ import annotations

import streamlit as st


def main() -> None:
    """Render the Phase 0 application shell."""
    st.set_page_config(page_title="GroundNote", page_icon="GN", layout="centered")

    st.title("GroundNote")
    st.subheader("Private, Offline RAG Study Assistant")
    st.info("The RAG engine is not configured yet.")


if __name__ == "__main__":
    main()
