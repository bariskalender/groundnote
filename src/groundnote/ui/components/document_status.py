"""Lightweight document status summary."""

from __future__ import annotations

import streamlit as st

from groundnote.ui.formatting import (
    format_file_size,
    format_file_type,
    format_status,
    format_timestamp,
    safe_filename,
)
from groundnote.ui.models import DocumentSummary


def render_document_status(documents: list[DocumentSummary]) -> None:
    """Render safe status fields without management controls."""
    st.subheader("Documents")
    if not documents:
        st.info("No documents have been added yet. Upload a document above to begin.")
        return
    rows = [
        {
            "Document": safe_filename(document.original_filename),
            "Type": format_file_type(document.file_type),
            "Status": format_status(document.status),
            "Size": format_file_size(document.file_size_bytes),
            "Pages": document.page_count if document.page_count is not None else "—",
            "Chunks": document.chunk_count,
            "Indexed": document.embedded_chunk_count,
            "Uploaded": format_timestamp(document.created_at),
            "Indexed at": format_timestamp(document.indexed_at),
            "Embedding model": document.embedding_model or "—",
        }
        for document in documents
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)
    failed = [document for document in documents if format_status(document.status) == "Failed"]
    for document in failed:
        st.warning(
            f"{safe_filename(document.original_filename)}: "
            f"{document.error_message or 'Local processing failed.'}"
        )
