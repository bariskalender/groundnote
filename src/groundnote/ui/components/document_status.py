"""Lightweight document status summary."""

from __future__ import annotations

import streamlit as st

from groundnote.ui.formatting import (
    format_status,
    safe_filename,
)
from groundnote.ui.models import DocumentSummary


def render_document_status(documents: list[DocumentSummary]) -> None:
    """Render a compact safe document list without technical index fields."""
    st.subheader("Documents")
    if not documents:
        st.info("No documents have been added yet. Upload a document above to begin.")
        return
    for document in documents:
        name_column, status_column = st.columns([4, 1])
        name_column.caption(f"📄 {safe_filename(document.original_filename)}")
        status_column.caption(format_status(document.status))
