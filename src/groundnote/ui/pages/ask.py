"""Single-turn grounded question view."""

from __future__ import annotations

import streamlit as st

from groundnote.domain import SupportedFileType
from groundnote.ui.app_context import ApplicationContext
from groundnote.ui.components.chat import render_question_input, render_question_outcome
from groundnote.ui.components.notices import render_message
from groundnote.ui.errors import map_exception
from groundnote.ui.formatting import format_file_type, safe_filename
from groundnote.ui.models import QuestionOutcome
from groundnote.ui.state import (
    CURRENT_FILTERS,
    LAST_QUESTION,
    LAST_RAG_ANSWER,
    QUESTION_IN_PROGRESS,
)
from groundnote.utils import get_logger


def render_ask_page(context: ApplicationContext) -> None:
    """Render indexed-source filters and one independent RAG request."""
    st.header("Ask GroundNote")
    st.write("GroundNote answers only from indexed documents.")
    try:
        indexed = context.document_workflow.indexed_documents()
    except Exception as exc:
        get_logger(__name__).warning("ask_source_refresh_failed", error_type=type(exc).__name__)
        render_message(map_exception(exc))
        return
    if not indexed:
        st.info("No indexed documents are ready. Add and index a document in the Documents view.")
        return

    document_map = {document.document_id: document for document in indexed}
    with st.expander("Source filters", expanded=False):
        selected_document_ids = st.multiselect(
            "Documents",
            options=list(document_map),
            format_func=lambda value: safe_filename(document_map[value].original_filename),
            help="Leave empty to search all indexed documents.",
        )
        available_types = sorted(
            {document.file_type for document in indexed},
            key=lambda item: item.value,
        )
        selected_file_types = st.multiselect(
            "File types",
            options=available_types,
            format_func=format_file_type,
            help="Leave empty to include every indexed file type.",
        )
    question = render_question_input(context.settings.rag_max_query_characters)
    if question is not None:
        _answer_question(
            context,
            question,
            document_ids=selected_document_ids,
            file_types=selected_file_types,
        )
    previous = st.session_state.get(LAST_RAG_ANSWER)
    if isinstance(previous, QuestionOutcome):
        render_question_outcome(previous)


def _answer_question(
    context: ApplicationContext,
    question: str,
    *,
    document_ids: list[str],
    file_types: list[SupportedFileType],
) -> None:
    if bool(st.session_state.get(QUESTION_IN_PROGRESS)):
        st.warning("A question is already being answered.")
        return
    st.session_state[QUESTION_IN_PROGRESS] = True
    with st.status(
        "Searching indexed documents and generating a local answer",
        expanded=True,
    ) as status:
        try:
            status.write("Searching the local semantic index")
            outcome = context.question_workflow.answer(
                question,
                document_ids=document_ids,
                file_types=file_types,
            )
            status.write("Validating grounded citations")
            st.session_state[LAST_QUESTION] = outcome.question
            st.session_state[LAST_RAG_ANSWER] = outcome
            st.session_state[CURRENT_FILTERS] = {
                "document_ids": list(outcome.document_ids),
                "file_types": [file_type.value for file_type in outcome.file_types],
            }
            status.update(label="Answer ready", state="complete", expanded=False)
        except Exception as exc:
            get_logger(__name__).warning("ui_question_failed", error_type=type(exc).__name__)
            status.update(label="Question could not be completed", state="error", expanded=True)
            render_message(map_exception(exc))
        finally:
            st.session_state[QUESTION_IN_PROGRESS] = False
