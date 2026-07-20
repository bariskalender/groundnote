"""GroundNote Streamlit application entrypoint."""

from __future__ import annotations

from uuid import uuid4

import streamlit as st

from groundnote.domain import DocumentStatus, SupportedFileType
from groundnote.ui import ApplicationContext, build_application_context, unload_local_models
from groundnote.ui.components.notices import render_message
from groundnote.ui.components.upload import render_upload_control
from groundnote.ui.errors import DatabaseBootstrapError, map_exception, safe_failure_message
from groundnote.ui.formatting import format_duration, format_file_type, safe_filename
from groundnote.ui.models import (
    ChatMessageState,
    DocumentSummary,
    QuestionOutcome,
    UploadOutcomeKind,
    UploadStage,
)
from groundnote.ui.state import (
    ACTIVE_OPERATION,
    ANSWER_LANGUAGE,
    CHAT_MESSAGES,
    CURRENT_FILTERS,
    PERFORMANCE_MODE,
    UI_LANGUAGE,
    begin_operation,
    end_operation,
    initialize_session_state,
    operation_is_active,
)
from groundnote.ui.text import t
from groundnote.ui.uploads import (
    SelectedUpload,
    UploadItemState,
    UploadStatus,
    complete_upload,
    fail_upload,
    queue_retry,
    read_uploaded_bytes,
    register_selected_uploads,
    start_upload,
    update_upload_status,
    upload_items,
)
from groundnote.utils import get_logger

PERFORMANCE_OPTIONS = ("Balanced", "Fast", "Memory saver")
ANSWER_LANGUAGE_OPTIONS = ("auto", "en", "tr")


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
        render_message(map_exception(error, _language()))
        return

    language = _render_header_and_settings(context)
    _render_chat_history(language)
    processing_notice = st.empty()
    _render_sidebar(context, language, processing_notice)
    _render_chat_input(context, language)


def _render_header_and_settings(context: ApplicationContext) -> str:
    title_column, settings_column = st.columns([12, 1], vertical_alignment="top")
    with title_column:
        st.title("GroundNote")
    with settings_column, st.popover("⚙️", help=t("settings_help", _language())):
        language = _language()
        st.selectbox(
            t("interface_language", language),
            options=["en", "tr"],
            format_func=lambda value: "Türkçe" if value == "tr" else "English",
            key=UI_LANGUAGE,
        )
        language = _language()
        st.selectbox(
            t("performance_mode", language),
            options=list(PERFORMANCE_OPTIONS),
            format_func=lambda value: _performance_label(str(value), language),
            key=PERFORMANCE_MODE,
        )
        st.selectbox(
            t("answer_language", language),
            options=list(ANSWER_LANGUAGE_OPTIONS),
            format_func=lambda value: t(f"answer_{value}", language),
            key=ANSWER_LANGUAGE,
        )
        if st.session_state.get(PERFORMANCE_MODE) == "Memory saver":
            st.caption(t("memory_saver_notice", language))
        st.caption(t("local_notice", language))
        if st.button(t("unload_models", language), use_container_width=True):
            warnings = unload_local_models(context)
            if warnings:
                st.warning(t("operation_reset", language))
            else:
                st.success(t("models_unloaded", language))
    return _language()


def _render_sidebar(
    context: ApplicationContext,
    language: str,
    processing_notice: object,
) -> None:
    with st.sidebar:
        if st.button(t("new_chat", language), use_container_width=True):
            st.session_state[CHAT_MESSAGES] = []
            st.rerun()

        st.subheader(t("upload_documents", language))
        uploaded = render_upload_control(context.settings.maximum_upload_size_mb, language)
        try:
            registration = register_selected_uploads(st.session_state, uploaded)
        except Exception as exc:
            message = safe_failure_message(
                exc,
                logger=get_logger(__name__),
                event="ui_upload_registration_failed",
                language=language,
            )
            render_message(message)
            registration = None

        selected: dict[str, SelectedUpload] = {}
        if registration is not None:
            selected = registration.selected
            if registration.queued:
                _notice(
                    processing_notice,
                    t("preparing_documents", language).format(count=len(registration.queued)),
                )
            for selection in registration.queued:
                _process_selected_upload(context, selection, language)
            _clear_notice(processing_notice)

        _render_document_list(context, language, selected)
        _render_sources_sidebar(context, language)
        _render_foundry_status(context, language)
        st.caption(t("local_notice", language))


def _process_selected_upload(
    context: ApplicationContext,
    selection: SelectedUpload,
    language: str,
) -> None:
    start_upload(st.session_state, selection.identity)
    operation = begin_operation(
        st.session_state,
        "upload",
        file_identity=selection.identity,
    )
    succeeded = False
    before_ids = _document_ids(context)
    with st.status(
        f"{t('validating_upload', language)}: {selection.filename}",
        expanded=False,
    ) as status:

        def show_stage(stage: UploadStage) -> None:
            upload_status = _upload_status_for_stage(stage)
            update_upload_status(st.session_state, selection.identity, upload_status)
            status.write(_upload_status_label(upload_status, language))

        data: bytes | None = None
        try:
            data = read_uploaded_bytes(selection.source)
            outcome = context.document_workflow.process_and_index(
                original_filename=selection.filename,
                data=data,
                on_stage=show_stage,
            )
            terminal_status = (
                UploadStatus.DUPLICATE
                if outcome.kind is UploadOutcomeKind.DUPLICATE
                else UploadStatus.READY
            )
            complete_upload(
                st.session_state,
                selection.identity,
                status=terminal_status,
                document_id=outcome.document.document_id,
            )
            status.update(
                label=f"{_upload_status_label(terminal_status, language)}: {selection.filename}",
                state="complete",
                expanded=False,
            )
            succeeded = True
        except Exception as exc:
            original_error = exc
            message = safe_failure_message(
                original_error,
                logger=get_logger(__name__),
                event="ui_document_operation_failed",
                language=language,
            )
            fail_upload(
                st.session_state,
                selection.identity,
                message=message,
                document_id=_new_failed_document_id(context, before_ids),
            )
            status.update(
                label=f"{t('failed', language)}: {selection.filename}",
                state="error",
                expanded=False,
            )
            render_message(message)
        finally:
            data = None
            end_operation(st.session_state, operation, succeeded=succeeded)


def _render_document_list(
    context: ApplicationContext,
    language: str,
    selected: dict[str, SelectedUpload],
) -> None:
    st.subheader(t("documents", language))
    try:
        documents = context.document_workflow.list_documents()
    except Exception as exc:
        render_message(
            safe_failure_message(
                exc,
                logger=get_logger(__name__),
                event="ui_document_status_failed",
                language=language,
            )
        )
        return

    session_items = upload_items(st.session_state)
    item_by_document = {
        item.document_id: item for item in session_items if item.document_id is not None
    }
    if not documents and not session_items:
        st.caption(t("no_documents", language))
        return

    for document in documents[:20]:
        item = item_by_document.get(document.document_id)
        _render_document_row(context, document, item, language, selected)

    represented = {document.document_id for document in documents}
    for item in session_items:
        if item.document_id in represented and item.status != UploadStatus.DUPLICATE:
            continue
        if item.status == UploadStatus.READY:
            continue
        _render_upload_item_row(context, item, language, selected)


def _render_document_row(
    context: ApplicationContext,
    document: DocumentSummary,
    item: UploadItemState | None,
    language: str,
    selected: dict[str, SelectedUpload],
) -> None:
    filename_column, status_column, action_column = st.columns([6, 3, 2])
    filename_column.caption(f"📄 {safe_filename(document.original_filename)}")
    status_column.caption(_document_status_label(document.status, language))
    if document.status == DocumentStatus.FAILED:
        identity = item.identity if item is not None else f"document-{document.document_id}"
        if action_column.button(t("retry", language), key=f"retry-{identity}"):
            _retry_index_document(context, document, item, language)


def _render_upload_item_row(
    context: ApplicationContext,
    item: UploadItemState,
    language: str,
    selected: dict[str, SelectedUpload],
) -> None:
    filename_column, status_column, action_column = st.columns([6, 3, 2])
    filename_column.caption(f"📄 {item.filename}")
    status_column.caption(_upload_status_label(item.status, language))
    if item.status != UploadStatus.FAILED:
        return
    selection = selected.get(item.identity)
    if action_column.button(
        t("retry", language),
        key=f"retry-upload-{item.identity}",
        disabled=selection is None,
    ):
        if item.document_id is not None:
            document = _document_by_id(context, item.document_id)
            if document is not None:
                _retry_index_document(context, document, item, language)
        elif selection is not None:
            queue_retry(st.session_state, item.identity)
            _process_selected_upload(context, selection, language)
            st.rerun()
    if selection is None:
        action_column.caption(t("reselect_retry", language))


def _retry_index_document(
    context: ApplicationContext,
    document: DocumentSummary,
    item: UploadItemState | None,
    language: str,
) -> None:
    identity = item.identity if item is not None else f"document-{document.document_id}"
    operation = begin_operation(st.session_state, "upload", file_identity=identity)
    succeeded = False
    try:
        context.indexing_service.index_document(
            document.document_id,
            force_reindex=document.status == DocumentStatus.FAILED,
        )
        if item is not None:
            complete_upload(
                st.session_state,
                item.identity,
                status=UploadStatus.READY,
                document_id=document.document_id,
            )
        succeeded = True
    except Exception as exc:
        message = safe_failure_message(
            exc,
            logger=get_logger(__name__),
            event="ui_document_retry_failed",
            language=language,
        )
        if item is not None:
            fail_upload(
                st.session_state,
                item.identity,
                message=message,
                document_id=document.document_id,
            )
        render_message(message)
    finally:
        end_operation(st.session_state, operation, succeeded=succeeded)
    if succeeded:
        st.rerun()


def _render_sources_sidebar(context: ApplicationContext, language: str) -> None:
    try:
        indexed = context.document_workflow.indexed_documents()
    except Exception as exc:
        render_message(
            safe_failure_message(
                exc,
                logger=get_logger(__name__),
                event="ui_source_refresh_failed",
                language=language,
            )
        )
        return
    with st.expander(t("sources", language), expanded=False):
        document_map = {document.document_id: document for document in indexed}
        current = st.session_state.get(CURRENT_FILTERS, {})
        current_ids = current.get("document_ids", []) if isinstance(current, dict) else []
        current_types = current.get("file_types", []) if isinstance(current, dict) else []
        selected_document_ids = st.multiselect(
            t("source_documents", language),
            options=list(document_map),
            default=[value for value in current_ids if value in document_map],
            format_func=lambda value: safe_filename(document_map[value].original_filename),
            help=t("all_sources_help", language),
        )
        available_types = sorted(
            {document.file_type for document in indexed},
            key=lambda item: item.value,
        )
        selected_file_types = st.multiselect(
            t("source_file_types", language),
            options=available_types,
            default=[
                SupportedFileType(value)
                for value in current_types
                if value in {item.value for item in available_types}
            ],
            format_func=format_file_type,
            help=t("all_sources_help", language),
        )
        active_count = len(selected_document_ids) or len(indexed)
        st.caption(t("active_sources", language).format(count=active_count))
        st.session_state[CURRENT_FILTERS] = {
            "document_ids": selected_document_ids,
            "file_types": [file_type.value for file_type in selected_file_types],
        }


def _render_foundry_status(context: ApplicationContext, language: str) -> None:
    status = context.foundry_status_service.check()
    st.caption(f"{t('foundry_status', language)}: {status.label}")
    if status.instruction:
        st.caption(status.instruction)


def _render_chat_history(language: str) -> None:
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


def _render_chat_input(context: ApplicationContext, language: str) -> None:
    active = operation_is_active(st.session_state.get(ACTIVE_OPERATION))
    prompt = st.chat_input(
        t("ask_placeholder", language),
        max_chars=context.settings.rag_max_query_characters,
        disabled=active,
    )
    if prompt:
        _answer_prompt(context, prompt, language)


def _answer_prompt(context: ApplicationContext, prompt: str, language: str) -> None:
    operation = begin_operation(st.session_state, "question")
    succeeded = False
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
        answer_setting = str(st.session_state.get(ANSWER_LANGUAGE, "auto"))
        response_language = answer_setting if answer_setting in {"en", "tr"} else None
        with st.chat_message("assistant"):
            with st.status(t("searching", language), expanded=False) as status:
                status.write(t("reading", language))
                status.write(t("generating", language))
                outcome = workflow.answer(
                    prompt,
                    document_ids=document_ids,
                    file_types=file_types,
                    response_language=response_language,
                )
                status.write(t("validating", language))
                status.update(label=t("ready", language), state="complete", expanded=False)
            st.markdown(outcome.answer.answer)
            message = _message_from_outcome(outcome)
            _append_message(message)
            _render_compact_citations(message, language)
            st.caption(format_duration(outcome.answer.duration_ms))
        succeeded = True
        if st.session_state.get(PERFORMANCE_MODE) == "Memory saver":
            unload_local_models(context)
    except Exception as exc:
        ui_message = safe_failure_message(
            exc,
            logger=get_logger(__name__),
            event="ui_question_failed",
            language=language,
        )
        with st.chat_message("assistant"):
            render_message(ui_message)
    finally:
        end_operation(st.session_state, operation, succeeded=succeeded)


def _render_compact_citations(message: ChatMessageState, language: str) -> None:
    if not message.citations:
        return
    labels: list[str] = []
    seen: set[tuple[str, int | None, str | None]] = set()
    for citation in message.citations:
        key = (citation.display_label, citation.page_number, citation.section_title)
        if key in seen:
            continue
        seen.add(key)
        labels.append(f"[{citation.citation_id}] {citation.display_label}")
    st.caption(f"{t('sources', language)}: " + " · ".join(labels))


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
    return [message for message in messages if isinstance(message, ChatMessageState)]


def _append_message(message: ChatMessageState) -> None:
    messages = _messages()
    messages.append(message)
    st.session_state[CHAT_MESSAGES] = messages


def _document_ids(context: ApplicationContext) -> set[str]:
    try:
        return {document.document_id for document in context.document_workflow.list_documents()}
    except Exception:
        return set()


def _new_failed_document_id(context: ApplicationContext, before_ids: set[str]) -> str | None:
    try:
        candidates = [
            document.document_id
            for document in context.document_workflow.list_documents()
            if document.document_id not in before_ids and document.status == DocumentStatus.FAILED
        ]
    except Exception:
        return None
    return candidates[0] if len(candidates) == 1 else None


def _document_by_id(
    context: ApplicationContext,
    document_id: str,
) -> DocumentSummary | None:
    try:
        return context.document_workflow.get_document(document_id)
    except Exception:
        return None


def _upload_status_for_stage(stage: UploadStage) -> UploadStatus:
    return {
        UploadStage.SAVING: UploadStatus.VALIDATING,
        UploadStage.PROCESSING: UploadStatus.PROCESSING,
        UploadStage.INDEXING: UploadStatus.INDEXING,
        UploadStage.FINALIZING: UploadStatus.INDEXING,
        UploadStage.READY: UploadStatus.READY,
    }[stage]


def _upload_status_label(status: UploadStatus, language: str) -> str:
    key = {
        UploadStatus.WAITING: "waiting",
        UploadStatus.VALIDATING: "validating_upload",
        UploadStatus.PROCESSING: "processing",
        UploadStatus.INDEXING: "indexing",
        UploadStatus.READY: "ready",
        UploadStatus.DUPLICATE: "duplicate",
        UploadStatus.FAILED: "failed",
    }[status]
    return t(key, language)


def _document_status_label(status: DocumentStatus, language: str) -> str:
    if status == DocumentStatus.INDEXED:
        return t("ready", language)
    if status == DocumentStatus.FAILED:
        return t("failed", language)
    if status == DocumentStatus.INDEXING:
        return t("indexing", language)
    if status in {DocumentStatus.PENDING, DocumentStatus.PENDING_EMBEDDING}:
        return t("waiting", language)
    return t("processing", language)


def _performance_label(value: str, language: str) -> str:
    return {
        "Fast": t("fast", language),
        "Balanced": t("balanced", language),
        "Memory saver": t("memory_saver", language),
    }.get(value, value)


def _notice(placeholder: object, message: str) -> None:
    info = getattr(placeholder, "info", None)
    if callable(info):
        info(message)


def _clear_notice(placeholder: object) -> None:
    empty = getattr(placeholder, "empty", None)
    if callable(empty):
        empty()


def _language() -> str:
    return "tr" if st.session_state.get(UI_LANGUAGE) == "tr" else "en"


if __name__ == "__main__":
    main()
