"""GroundNote Streamlit application entrypoint."""

from __future__ import annotations

from uuid import uuid4

import streamlit as st

from groundnote.domain import DocumentStatus, SupportedFileType
from groundnote.ui import ApplicationContext, build_application_context, unload_local_models
from groundnote.ui.components.notices import render_message
from groundnote.ui.components.upload import render_upload_control
from groundnote.ui.errors import DatabaseBootstrapError, map_exception
from groundnote.ui.formatting import format_duration, format_file_type, format_status, safe_filename
from groundnote.ui.models import ChatMessageState, QuestionOutcome, UploadOutcome, UploadOutcomeKind
from groundnote.ui.state import (
    ACTIVE_OPERATION,
    CHAT_MESSAGES,
    CURRENT_FILTERS,
    LAST_UPLOAD_RESULT,
    PERFORMANCE_MODE,
    UI_LANGUAGE,
    begin_operation,
    end_operation,
    initialize_session_state,
    operation_is_active,
)
from groundnote.ui.text import t
from groundnote.utils import get_logger


@st.cache_resource(show_spinner=False)
def get_application_context() -> ApplicationContext:
    """Cache stateless service composition, never private request data or model instances."""
    return build_application_context()


def main() -> None:
    """Render the chat-first local document assistant."""
    st.set_page_config(
        page_title="GroundNote",
        page_icon="GN",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    initialize_session_state(st.session_state)
    try:
        context = get_application_context()
    except Exception as exc:
        error = DatabaseBootstrapError("Application bootstrap failed.")
        error.__cause__ = exc
        render_message(map_exception(error))
        return

    language = _sidebar(context)
    _render_chat(context, language)


def _sidebar(context: ApplicationContext) -> str:
    with st.sidebar:
        st.title("GroundNote")
        if st.button(t("new_chat", _language()), use_container_width=True):
            st.session_state[CHAT_MESSAGES] = []
            st.session_state[CURRENT_FILTERS] = {"document_ids": [], "file_types": []}
            st.rerun()

        selected_language = st.selectbox(
            t("language", _language()),
            options=["English", "Türkçe"],
            index=0 if st.session_state.get(UI_LANGUAGE) == "en" else 1,
        )
        st.session_state[UI_LANGUAGE] = "tr" if selected_language == "Türkçe" else "en"
        language = _language()

        performance = st.selectbox(
            t("performance_mode", language),
            options=["Balanced", "Fast", "Memory saver"],
            index=["Balanced", "Fast", "Memory saver"].index(
                str(st.session_state.get(PERFORMANCE_MODE, "Balanced"))
            ),
        )
        st.session_state[PERFORMANCE_MODE] = performance
        if performance == "Memory saver":
            st.caption(t("memory_saver_notice", language))

        _render_foundry_status(context, language)
        _render_upload_sidebar(context, language)
        _render_sources_sidebar(context, language)

        with st.expander(t("settings", language), expanded=False):
            st.caption(t("local_notice", language))
            st.caption(f"{context.settings.embedding_model} · {context.settings.chat_model}")
            if st.button(t("unload_models", language), use_container_width=True):
                warnings = unload_local_models(context)
                if warnings:
                    st.warning(", ".join(warnings))
                else:
                    st.success(t("ready", language))
    return language


def _render_foundry_status(context: ApplicationContext, language: str) -> None:
    status = context.foundry_status_service.check()
    st.caption(f"{t('foundry_status', language)}: {status.label}")
    if status.instruction:
        st.caption(status.instruction)


def _render_upload_sidebar(context: ApplicationContext, language: str) -> None:
    with st.expander(t("upload_documents", language), expanded=True):
        uploaded, confirmed = render_upload_control(context.settings.maximum_upload_size_mb)
        if confirmed and uploaded:
            operation = begin_operation(st.session_state, "upload")
            try:
                for file in uploaded:
                    _process_one_upload(context, file)
            finally:
                end_operation(st.session_state, operation)
        previous = st.session_state.get(LAST_UPLOAD_RESULT)
        if isinstance(previous, UploadOutcome):
            label = safe_filename(previous.document.original_filename)
            if previous.kind is UploadOutcomeKind.DUPLICATE:
                st.info(f"{t('duplicate_document', language)}: {label}")
            else:
                st.success(f"{t('ready', language)}: {label}")


def _process_one_upload(context: ApplicationContext, uploaded: object) -> None:
    name = str(getattr(uploaded, "name", ""))
    getvalue = getattr(uploaded, "getvalue", None)
    if not callable(getvalue):
        raise RuntimeError("Uploaded content is unavailable.")
    with st.status(f"Indexing {safe_filename(name)}", expanded=False) as status:
        try:
            outcome = context.document_workflow.process_and_index(
                original_filename=name,
                data=bytes(getvalue()),
                on_stage=lambda stage: status.write(stage.value),
            )
            st.session_state[LAST_UPLOAD_RESULT] = outcome
            label = "Duplicate document" if outcome.kind is UploadOutcomeKind.DUPLICATE else "Ready"
            status.update(label=f"{label}: {safe_filename(name)}", state="complete", expanded=False)
        except Exception as exc:
            get_logger(__name__).warning(
                "ui_document_operation_failed",
                error_type=type(exc).__name__,
            )
            status.update(label=f"Failed: {safe_filename(name)}", state="error", expanded=True)
            render_message(map_exception(exc))


def _render_sources_sidebar(context: ApplicationContext, language: str) -> None:
    try:
        documents = context.document_workflow.list_documents()
    except Exception as exc:
        render_message(map_exception(exc))
        return
    indexed = [document for document in documents if document.status is DocumentStatus.INDEXED]
    with st.expander(t("indexed_documents", language), expanded=True):
        if not indexed:
            st.info(t("no_indexed_documents", language))
        else:
            for document in indexed[:12]:
                st.caption(
                    f"{safe_filename(document.original_filename)} · "
                    f"{format_status(document.status)} · {document.chunk_count} chunks"
                )
    with st.expander(t("sources", language), expanded=False):
        document_map = {document.document_id: document for document in indexed}
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
        st.caption(f"{len(selected_document_ids) or len(indexed)} active source(s)")
        st.session_state[CURRENT_FILTERS] = {
            "document_ids": selected_document_ids,
            "file_types": [file_type.value for file_type in selected_file_types],
        }
    with st.expander(t("retry", language), expanded=False):
        retryable = [
            document
            for document in documents
            if document.status in {DocumentStatus.FAILED, DocumentStatus.PENDING_EMBEDDING}
        ]
        for document in retryable:
            if st.button(
                safe_filename(document.original_filename),
                key=f"retry-{document.document_id}",
            ):
                try:
                    context.indexing_service.index_document(
                        document.document_id,
                        force_reindex=document.status is DocumentStatus.FAILED,
                    )
                    st.rerun()
                except Exception as exc:
                    render_message(map_exception(exc))


def _render_chat(context: ApplicationContext, language: str) -> None:
    st.title("GroundNote")
    messages = _messages()
    if not messages:
        with st.chat_message("assistant"):
            st.markdown(t("assistant_greeting", language))
    for message in messages:
        with st.chat_message(message.role):
            st.markdown(message.text)
            if message.role == "assistant":
                _render_compact_citations(message, language)
                if message.duration_ms is not None:
                    st.caption(format_duration(message.duration_ms))
                if message.warnings:
                    with st.expander(t("technical_details", language), expanded=False):
                        for warning in message.warnings:
                            st.caption(warning)

    active = operation_is_active(st.session_state.get(ACTIVE_OPERATION))
    prompt = st.chat_input(t("ask_placeholder", language), disabled=active)
    if prompt:
        _answer_prompt(context, prompt, language)


def _answer_prompt(context: ApplicationContext, prompt: str, language: str) -> None:
    operation = begin_operation(st.session_state, "question")
    _append_message(ChatMessageState(message_id=str(uuid4()), role="user", text=prompt.strip()))
    with st.chat_message("user"):
        st.markdown(prompt.strip())
    try:
        filters = st.session_state.get(CURRENT_FILTERS, {})
        document_ids = list(filters.get("document_ids", [])) if isinstance(filters, dict) else []
        raw_types = list(filters.get("file_types", [])) if isinstance(filters, dict) else []
        file_types = [SupportedFileType(value) for value in raw_types]
        workflow = (
            context.fast_question_workflow
            if st.session_state.get(PERFORMANCE_MODE) == "Fast"
            else context.question_workflow
        )
        with st.chat_message("assistant"):
            with st.status(t("searching", language), expanded=False) as status:
                status.write(t("reading", language))
                status.write(t("generating", language))
                outcome = workflow.answer(
                    prompt,
                    document_ids=document_ids,
                    file_types=file_types,
                    response_language=language,
                )
                status.write(t("validating", language))
                status.update(label=t("ready", language), state="complete", expanded=False)
            st.markdown(outcome.answer.answer)
            message = _message_from_outcome(outcome)
            _append_message(message)
            _render_compact_citations(message, language)
            st.caption(format_duration(outcome.answer.duration_ms))
        if st.session_state.get(PERFORMANCE_MODE) == "Memory saver":
            unload_local_models(context)
    except Exception as exc:
        get_logger(__name__).warning("ui_question_failed", error_type=type(exc).__name__)
        with st.chat_message("assistant"):
            render_message(map_exception(exc))
    finally:
        end_operation(st.session_state, operation)


def _render_compact_citations(message: ChatMessageState, language: str) -> None:
    if not message.citations:
        return
    st.caption(
        f"{t('sources', language)}: "
        + " · ".join(
            f"[{citation.citation_id}] {citation.display_label}" for citation in message.citations
        )
    )
    with st.expander(t("technical_details", language), expanded=False):
        for citation in message.citations:
            score = "" if citation.score is None else f" · score {citation.score:.3f}"
            st.caption(f"{citation.citation_id}: {citation.source_file_type.value}{score}")


def _message_from_outcome(outcome: QuestionOutcome) -> ChatMessageState:
    return ChatMessageState(
        message_id=str(uuid4()),
        role="assistant",
        text=outcome.answer.answer,
        citations=tuple(outcome.answer.citations),
        status="insufficient" if outcome.answer.insufficient_evidence else "complete",
        duration_ms=outcome.answer.duration_ms,
        warnings=tuple(outcome.answer.warnings),
    )


def _messages() -> list[ChatMessageState]:
    messages = st.session_state.get(CHAT_MESSAGES, [])
    if not isinstance(messages, list):
        st.session_state[CHAT_MESSAGES] = []
        return []
    return messages


def _append_message(message: ChatMessageState) -> None:
    messages = _messages()
    messages.append(message)
    st.session_state[CHAT_MESSAGES] = messages


def _language() -> str:
    return "tr" if st.session_state.get(UI_LANGUAGE) == "tr" else "en"


if __name__ == "__main__":
    main()
