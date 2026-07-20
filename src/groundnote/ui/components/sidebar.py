"""Sidebar navigation and local-runtime summary."""

from __future__ import annotations

import streamlit as st

from groundnote.ui.app_context import ApplicationContext
from groundnote.ui.foundry_status import FoundryStatusKind
from groundnote.ui.state import ACTIVE_PAGE

PAGES = ("Documents", "Ask GroundNote")


def render_sidebar(context: ApplicationContext) -> str:
    """Render navigation and return the active page label."""
    with st.sidebar:
        st.header("GroundNote")
        st.caption("Your documents and model requests stay on this computer.")
        status = context.foundry_status_service.check()
        if status.kind is FoundryStatusKind.READY:
            st.success(f"Foundry Local: {status.label}")
        elif status.kind is FoundryStatusKind.NOT_RUNNING:
            st.warning(f"Foundry Local: {status.label}")
        else:
            st.info(f"Foundry Local: {status.label}")
        if status.instruction:
            st.caption(status.instruction)
        page = st.radio("Navigate", PAGES, key=ACTIVE_PAGE)
        st.divider()
        st.caption("Supported: PDF, DOCX, TXT, Markdown")
        st.caption("OCR is not supported. Scanned PDFs may not contain readable text.")
        st.caption(
            f"Local models: {context.settings.embedding_model} · {context.settings.chat_model}"
        )
    return str(page)
