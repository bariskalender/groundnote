"""Minimal Streamlit application shell for GroundNote."""

from __future__ import annotations

import streamlit as st

from groundnote.bootstrap import initialize_application


def main() -> None:
    """Render the Phase 0 application shell."""
    st.set_page_config(page_title="GroundNote", page_icon="GN", layout="centered")

    st.title("GroundNote")
    st.subheader("Private, Offline RAG Study Assistant")
    try:
        initialize_application()
    except Exception as exc:
        st.error("GroundNote could not initialize local settings or storage.")
        st.caption(type(exc).__name__)
        return

    st.info("The RAG engine is not configured yet.")
    st.caption("Local configuration and SQLite storage are initialized.")


if __name__ == "__main__":
    main()
