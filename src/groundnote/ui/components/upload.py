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
from groundnote.ui.text import t

SUPPORTED_EXTENSIONS = ["pdf", "docx", "txt", "md", "markdown"]


def render_upload_control(
    maximum_size_mb: int,
    language: str = "en",
    *,
    disabled: bool = False,
    key: str | None = None,
) -> Any | None:
    """Render one file selector whose selection is processed automatically."""
    st.caption(t("upload_help", language))
    st.caption(t("upload_limit", language).format(size=maximum_size_mb))
    uploaded_file = st.file_uploader(
        "PDF, DOCX, TXT, or Markdown",
        type=SUPPORTED_EXTENSIONS,
        accept_multiple_files=False,
        help="OCR is not supported. Use text-based PDFs.",
        disabled=disabled,
        key=key,
    )
    return uploaded_file


def render_upload_outcome(outcome: UploadOutcome) -> None:
    """Render a compact completed success or duplicate result from safe metadata."""
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
    st.caption(
        f"{format_file_size(document.file_size_bytes)} · {format_duration(outcome.duration_ms)}"
    )
