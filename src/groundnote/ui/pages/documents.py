"""Documents upload and indexing view."""

from __future__ import annotations

import streamlit as st

from groundnote.ui.app_context import ApplicationContext
from groundnote.ui.components.document_status import render_document_status
from groundnote.ui.components.notices import render_message, render_warnings
from groundnote.ui.components.upload import render_upload_control, render_upload_outcome
from groundnote.ui.errors import map_exception
from groundnote.ui.models import UploadOutcome, UploadOutcomeKind, UploadStage
from groundnote.ui.state import (
    INDEXING_IN_PROGRESS,
    LAST_INDEXING_RESULT,
    LAST_UPLOAD_RESULT,
    LAST_UPLOADED_DOCUMENT_ID,
    UPLOAD_IN_PROGRESS,
)
from groundnote.utils import get_logger


def render_documents_page(context: ApplicationContext) -> None:
    """Render confirmed one-file processing and current document status."""
    st.header("Documents")
    st.caption("Uploads remain local. OCR is not supported in this version.")
    uploaded, confirmed = render_upload_control(context.settings.maximum_upload_size_mb)
    if confirmed and uploaded:
        for file in uploaded:
            _process_upload(context, file)
    previous = st.session_state.get(LAST_UPLOAD_RESULT)
    if isinstance(previous, UploadOutcome):
        render_upload_outcome(previous)
        render_warnings(previous.warnings)
    if st.button("Refresh document status"):
        st.toast("Document status refreshed.")
    try:
        render_document_status(context.document_workflow.list_documents())
    except Exception as exc:
        get_logger(__name__).warning(
            "document_status_refresh_failed",
            error_type=type(exc).__name__,
        )
        render_message(map_exception(exc))


def _process_upload(context: ApplicationContext, uploaded: object) -> None:
    if bool(st.session_state.get(UPLOAD_IN_PROGRESS)):
        st.warning("A document operation is already in progress.")
        return
    st.session_state[UPLOAD_IN_PROGRESS] = True
    st.session_state[INDEXING_IN_PROGRESS] = False
    status = st.status("Processing document locally", expanded=True)

    def show_stage(stage: UploadStage) -> None:
        st.session_state[INDEXING_IN_PROGRESS] = stage is UploadStage.INDEXING
        status.write(stage.value)

    try:
        name = str(getattr(uploaded, "name", ""))
        getvalue = getattr(uploaded, "getvalue", None)
        if not callable(getvalue):
            raise RuntimeError("Uploaded content is unavailable.")
        data = bytes(getvalue())
        outcome = context.document_workflow.process_and_index(
            original_filename=name,
            data=data,
            on_stage=show_stage,
        )
        st.session_state[LAST_UPLOAD_RESULT] = outcome
        st.session_state[LAST_UPLOADED_DOCUMENT_ID] = outcome.document.document_id
        st.session_state[LAST_INDEXING_RESULT] = outcome.document.status.value
        if outcome.kind is UploadOutcomeKind.DUPLICATE:
            status.update(label="Duplicate document detected", state="complete", expanded=False)
        else:
            status.update(label="Document indexed successfully", state="complete", expanded=False)
    except Exception as exc:
        get_logger(__name__).warning("ui_document_operation_failed", error_type=type(exc).__name__)
        status.update(label="Document processing failed", state="error", expanded=True)
        render_message(map_exception(exc))
    finally:
        st.session_state[UPLOAD_IN_PROGRESS] = False
        st.session_state[INDEXING_IN_PROGRESS] = False
