"""Document upload controls and result rendering."""

from __future__ import annotations

from typing import Any

import streamlit as st

from groundnote.ui.formatting import (
    format_duration,
    format_file_size,
    format_file_type,
    format_status,
    safe_filename,
)
from groundnote.ui.models import UploadOutcome, UploadOutcomeKind

SUPPORTED_EXTENSIONS = ["pdf", "docx", "txt", "md", "markdown"]


def render_upload_control(maximum_size_mb: int) -> tuple[list[Any], bool]:
    """Render multiple-file upload selection and explicit confirmation action."""
    st.subheader("Upload documents")
    st.write(f"Choose supported files. The configured maximum size is {maximum_size_mb} MB.")
    st.caption("The browser file type is not trusted; GroundNote validates the content locally.")
    uploaded_files = st.file_uploader(
        "PDF, DOCX, TXT, or Markdown",
        type=SUPPORTED_EXTENSIONS,
        accept_multiple_files=True,
        help="OCR is not supported. Use text-based PDFs.",
    )
    uploaded = list(uploaded_files or [])
    if uploaded:
        st.caption(f"{len(uploaded)} file(s) selected.")
        for file in uploaded:
            st.caption(str(getattr(file, "name", "selected file")))
    confirmed = st.button(
        "Process documents",
        type="primary",
        disabled=not uploaded,
        use_container_width=False,
    )
    return uploaded, confirmed


def render_upload_outcome(outcome: UploadOutcome) -> None:
    """Render a completed success or duplicate result from safe metadata."""
    document = outcome.document
    if outcome.kind is UploadOutcomeKind.DUPLICATE:
        st.info(
            "**This document has already been added to GroundNote.**\n\n"
            f"{safe_filename(document.original_filename)} is currently "
            f"**{format_status(document.status)}**. Identical content was not processed again."
        )
        return
    st.success("Document indexed successfully.")
    first, second, third = st.columns(3)
    first.metric("File", safe_filename(document.original_filename))
    second.metric("Type", format_file_type(document.file_type))
    third.metric("Status", format_status(document.status))
    details = {
        "Size": format_file_size(document.file_size_bytes),
        "Pages": document.page_count if document.page_count is not None else "Not available",
        "Sections": outcome.section_count if outcome.section_count is not None else "Not available",
        "Chunks": document.chunk_count,
        "Indexed chunks": document.embedded_chunk_count,
        "Embedding model": document.embedding_model or "Not available",
        "Duration": format_duration(outcome.duration_ms),
    }
    st.table([details])
