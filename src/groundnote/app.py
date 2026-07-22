"""GroundNote Streamlit application entrypoint."""

from __future__ import annotations

import hashlib
import os
import time
from uuid import uuid4

import streamlit as st

from groundnote import __version__
from groundnote.domain import DocumentStatus, SupportedFileType
from groundnote.ui import ApplicationContext, build_application_context, unload_local_models
from groundnote.ui.components.notices import render_message
from groundnote.ui.components.upload import render_upload_control
from groundnote.ui.errors import DatabaseBootstrapError, map_exception, safe_failure_message
from groundnote.ui.formatting import format_duration, format_file_type, safe_filename
from groundnote.ui.foundry_status import FoundryStatusKind
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
    LAST_MODEL_ACTIVITY_AT,
    PENDING_CLEAR_DOCUMENTS,
    PENDING_DELETE_DOCUMENT_ID,
    PERFORMANCE_MODE,
    SHOW_DEBUG_DETAILS,
    UI_LANGUAGE,
    FlashNotice,
    FlashSeverity,
    begin_operation,
    can_start_new_chat,
    can_start_operation,
    clear_chat_messages,
    end_operation,
    initialize_session_state,
    operation_is_active,
    pop_flash_notice,
    reset_upload_widget,
    set_flash_notice,
    upload_widget_key,
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
BALANCED_MODEL_IDLE_TTL_SECONDS = 120.0
FAST_MODEL_IDLE_TTL_SECONDS = 300.0
MEMORY_SAVER_MODEL_IDLE_TTL_SECONDS = 15.0


@st.cache_resource(show_spinner=False)
def get_application_context(configuration_key: str = "default") -> ApplicationContext:
    """Cache stateless service composition, never private request data or model instances."""
    del configuration_key
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
        context = get_application_context(_application_context_cache_key())
    except Exception as exc:
        error = DatabaseBootstrapError("Application bootstrap failed.")
        error.__cause__ = exc
        render_message(map_exception(error, _language()))
        return

    language = _render_header_and_settings(context)
    _render_flash_notice()
    _cleanup_idle_models(context)
    _render_chat_history(context, language)
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
        st.toggle(t("show_debug_details", language), key=SHOW_DEBUG_DETAILS)
        st.caption(f"GroundNote {__version__}")
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
        new_chat_allowed = can_start_new_chat(st.session_state)
        if st.button(
            t("new_chat", language),
            use_container_width=True,
            disabled=not new_chat_allowed,
        ):
            clear_chat_messages(st.session_state)
            st.rerun()
        if not new_chat_allowed:
            st.caption(t("new_chat_busy", language))

        st.subheader(t("upload_documents", language))
        document_operation_active = operation_is_active(st.session_state.get(ACTIVE_OPERATION))
        uploaded = render_upload_control(
            context.settings.maximum_upload_size_mb,
            language,
            disabled=document_operation_active,
            key=upload_widget_key(st.session_state),
        )
        try:
            registration = register_selected_uploads(
                st.session_state,
                uploaded,
                block_new=document_operation_active,
            )
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
            if registration.blocked_count:
                st.info(t("operation_busy_upload", language))
                reset_upload_widget(st.session_state)
            selected = registration.selected
            if registration.queued:
                _notice(
                    processing_notice,
                    t("preparing_documents", language).format(count=len(registration.queued)),
                )
            queued = registration.queued
            if queued and operation_is_active(st.session_state.get(ACTIVE_OPERATION)):
                st.warning(t("operation_busy_indexing", language))
                queued = ()
            for selection in queued:
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
    if not can_start_operation(st.session_state):
        st.info(t("operation_busy_upload", language))
        return
    start_upload(st.session_state, selection.identity)
    _unload_chat_models(context)
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
            _mark_model_activity()
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
    st.subheader(t("knowledge_base", language))
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

    if documents:
        _render_clear_all_documents(context, documents, language)
        st.caption(t("indexed_documents", language))

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
    if not can_start_operation(st.session_state):
        st.info(t("operation_busy_indexing", language))
        return
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
    if status.kind is not FoundryStatusKind.READY:
        st.caption(t("groundnote_not_ready", language))


def _render_chat_history(context: ApplicationContext, language: str) -> None:
    messages = _messages()
    if not messages:
        with st.chat_message("assistant"):
            st.markdown(t("assistant_greeting", language))
            st.caption(t("current_chat", language))
            try:
                has_documents = bool(context.document_workflow.indexed_documents())
            except Exception:
                has_documents = False
            st.caption(
                t(
                    "empty_chat_with_documents" if has_documents else "empty_chat_no_documents",
                    language,
                )
            )
    for message in messages:
        with st.chat_message(message.role):
            st.markdown(message.text)
            if message.role == "assistant":
                _render_compact_citations(message, language)
                if message.duration_ms is not None:
                    st.caption(format_duration(message.duration_ms))
                if message.warnings and st.session_state.get(SHOW_DEBUG_DETAILS):
                    with st.expander(t("technical_details", language), expanded=False):
                        for warning in message.warnings:
                            st.caption(warning)


def _render_chat_input(context: ApplicationContext, language: str) -> None:
    active = operation_is_active(st.session_state.get(ACTIVE_OPERATION))
    if active:
        st.caption(t("operation_busy_question", language))
    prompt = st.chat_input(
        t("ask_placeholder", language),
        max_chars=context.settings.rag_max_query_characters,
        disabled=active,
    )
    if prompt:
        if not can_start_operation(st.session_state):
            st.info(t("operation_busy_question", language))
            return
        _answer_prompt(context, prompt, language)


def _answer_prompt(context: ApplicationContext, prompt: str, language: str) -> None:
    if not can_start_operation(st.session_state):
        st.info(t("operation_busy_question", language))
        return
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
        _mark_model_activity()
        if st.session_state.get(PERFORMANCE_MODE) == "Memory saver":
            unload_local_models(context)
            _mark_model_activity(clear=True)
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
        return t("retry_required", language)
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


def _application_context_cache_key() -> str:
    """Separate cached app composition when local path configuration changes."""
    material = "|".join(
        os.environ.get(name, "")
        for name in (
            "GROUNDNOTE_DATA_DIR",
            "GROUNDNOTE_DATA_DIRECTORY",
            "GROUNDNOTE_DATABASE_PATH",
        )
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _render_document_row(  # type: ignore[no-redef]
    context: ApplicationContext,
    document: DocumentSummary,
    item: UploadItemState | None,
    language: str,
    selected: dict[str, SelectedUpload],
) -> None:
    """Render one responsive card with vertically stacked full-width actions."""
    with st.container(border=True):
        document_action_busy = not can_start_operation(st.session_state)
        st.caption(f"📄 {safe_filename(document.original_filename)}")
        st.caption(_document_status_label(document.status, language))
        if document.status == DocumentStatus.FAILED:
            message_key = (
                "indexing_interrupted"
                if document.error_message and "interrupted" in document.error_message.casefold()
                else "document_not_ready"
            )
            st.caption(t(message_key, language))
        with st.expander(t("document_metadata", language), expanded=False):
            metadata = [
                t("document_type", language).format(file_type=format_file_type(document.file_type)),
                t("document_chunks", language).format(count=document.chunk_count),
            ]
            if document.page_count is not None:
                metadata.append(t("document_pages", language).format(count=document.page_count))
            if document.indexed_at is not None:
                metadata.append(
                    t("indexed_at", language).format(
                        timestamp=document.indexed_at.astimezone().strftime("%Y-%m-%d %H:%M")
                    )
                )
            else:
                metadata.append(t("not_indexed_yet", language))
            for value in metadata:
                st.caption(value)

        pending_delete = st.session_state.get(PENDING_DELETE_DOCUMENT_ID)
        if pending_delete == document.document_id:
            st.caption(t("confirm_delete_document", language))
            if st.button(
                t("delete_confirm", language),
                key=f"confirm-delete-{document.document_id}",
                use_container_width=True,
                type="primary",
                disabled=document_action_busy,
            ):
                _delete_document(context, document, language)
            if st.button(
                t("delete_cancel", language),
                key=f"cancel-delete-{document.document_id}",
                use_container_width=True,
            ):
                st.session_state[PENDING_DELETE_DOCUMENT_ID] = None
                st.rerun()
            return
        if st.button(
            t("delete_document", language),
            key=f"delete-{document.document_id}",
            use_container_width=True,
            disabled=document_action_busy,
        ):
            st.session_state[PENDING_DELETE_DOCUMENT_ID] = document.document_id
            st.rerun()
        if st.button(
            t("reindex_document", language),
            key=f"reindex-{document.document_id}",
            use_container_width=True,
            disabled=document_action_busy
            or document.status in {DocumentStatus.PENDING, DocumentStatus.INDEXING},
        ):
            _reindex_document(context, document, language)
        if document.status == DocumentStatus.FAILED:
            identity = item.identity if item is not None else f"document-{document.document_id}"
            if st.button(
                t("retry", language),
                key=f"retry-{identity}",
                use_container_width=True,
                disabled=document_action_busy,
            ):
                _retry_index_document(context, document, item, language)


def _delete_document(
    context: ApplicationContext,
    document: DocumentSummary,
    language: str,
) -> None:
    if not can_start_operation(st.session_state):
        st.info(t("operation_busy_indexing", language))
        return
    operation = begin_operation(st.session_state, "delete")
    succeeded = False
    try:
        deleted = context.document_workflow.delete_document(document.document_id)
        _remove_deleted_document_from_session(deleted.document_id)
        st.session_state[PENDING_DELETE_DOCUMENT_ID] = None
        set_flash_notice(
            st.session_state,
            FlashNotice(
                message=(
                    t("managed_copy_cleanup_warning", language)
                    if deleted.managed_copy_cleanup_warning
                    else t("document_deleted", language).format(
                        filename=safe_filename(deleted.original_filename)
                    )
                ),
                severity=(
                    FlashSeverity.WARNING
                    if deleted.managed_copy_cleanup_warning
                    else FlashSeverity.SUCCESS
                ),
            ),
        )
        succeeded = True
    except Exception as exc:
        render_message(
            safe_failure_message(
                exc,
                logger=get_logger(__name__),
                event="ui_document_delete_failed",
                language=language,
            )
        )
    finally:
        end_operation(st.session_state, operation, succeeded=succeeded)
    if succeeded:
        st.rerun()


def _reindex_document(
    context: ApplicationContext,
    document: DocumentSummary,
    language: str,
) -> None:
    """Regenerate embeddings sequentially for one existing document."""
    if not can_start_operation(st.session_state):
        st.info(t("operation_busy_indexing", language))
        return
    operation = begin_operation(st.session_state, "reindex")
    succeeded = False
    rerun_with_feedback = False
    try:
        with st.status(
            t("reindexing_document", language).format(
                filename=safe_filename(document.original_filename)
            ),
            expanded=False,
        ) as status:
            refreshed = context.document_workflow.reindex_document(document.document_id)
            status.update(label=t("ready", language), state="complete", expanded=False)
        set_flash_notice(
            st.session_state,
            FlashNotice(
                message=t("document_reindexed", language).format(
                    filename=safe_filename(refreshed.original_filename)
                ),
                severity=FlashSeverity.SUCCESS,
            ),
        )
        succeeded = True
        rerun_with_feedback = True
        _mark_model_activity()
    except Exception as exc:
        message = safe_failure_message(
            exc,
            logger=get_logger(__name__),
            event="ui_document_reindex_failed",
            language=language,
        )
        set_flash_notice(
            st.session_state,
            FlashNotice(
                title=message.title,
                message=message.message,
                remediation=message.remediation,
                severity=FlashSeverity.ERROR,
            ),
        )
        rerun_with_feedback = True
    finally:
        end_operation(st.session_state, operation, succeeded=succeeded)
    if rerun_with_feedback:
        st.rerun()


def _render_flash_notice() -> None:
    """Render one safe operation result after rerun, then consume it."""
    notice = pop_flash_notice(st.session_state)
    if notice is None:
        return
    body = notice.message
    if notice.title:
        body = f"**{notice.title}**\n\n{body}"
    if notice.remediation:
        body = f"{body}\n\n{notice.remediation}"
    renderer = {
        FlashSeverity.SUCCESS: st.success,
        FlashSeverity.INFO: st.info,
        FlashSeverity.WARNING: st.warning,
        FlashSeverity.ERROR: st.error,
    }[notice.severity]
    renderer(body)


def _render_clear_all_documents(
    context: ApplicationContext,
    documents: list[DocumentSummary],
    language: str,
) -> None:
    """Render a deliberately confirmed local-index-only bulk removal action."""
    pending = bool(st.session_state.get(PENDING_CLEAR_DOCUMENTS))
    if not pending:
        if st.button(
            t("clear_all_documents", language),
            key="clear-all-documents",
            use_container_width=True,
            disabled=not can_start_operation(st.session_state),
        ):
            st.session_state[PENDING_CLEAR_DOCUMENTS] = True
            st.rerun()
        return
    st.warning(t("clear_all_warning", language))
    st.caption(t("confirm_clear_all_documents", language))
    confirm_column, cancel_column = st.columns(2)
    if confirm_column.button(
        t("clear_all_confirm", language),
        key="confirm-clear-all-documents",
        type="primary",
        disabled=not can_start_operation(st.session_state),
    ):
        _clear_all_documents(context, documents, language)
    if cancel_column.button(t("delete_cancel", language), key="cancel-clear-all-documents"):
        st.session_state[PENDING_CLEAR_DOCUMENTS] = False
        st.rerun()


def _clear_all_documents(
    context: ApplicationContext,
    documents: list[DocumentSummary],
    language: str,
) -> None:
    if not can_start_operation(st.session_state):
        st.info(t("operation_busy_indexing", language))
        return
    operation = begin_operation(st.session_state, "clear_documents")
    succeeded = False
    try:
        deleted = context.document_workflow.clear_all_documents()
        _clear_document_references_from_session({item.document_id for item in deleted})
        st.session_state[PENDING_CLEAR_DOCUMENTS] = False
        warning_count = sum(item.managed_copy_cleanup_warning for item in deleted)
        set_flash_notice(
            st.session_state,
            FlashNotice(
                message=(
                    t("managed_copies_cleanup_warning", language).format(
                        count=len(deleted),
                        warning_count=warning_count,
                    )
                    if warning_count
                    else t("documents_cleared", language).format(count=len(deleted))
                ),
                severity=(FlashSeverity.WARNING if warning_count else FlashSeverity.SUCCESS),
            ),
        )
        succeeded = True
    except Exception as exc:
        render_message(
            safe_failure_message(
                exc,
                logger=get_logger(__name__),
                event="ui_documents_clear_failed",
                language=language,
            )
        )
    finally:
        end_operation(st.session_state, operation, succeeded=succeeded)
    if succeeded:
        st.rerun()


def _remove_deleted_document_from_session(document_id: str) -> None:
    _clear_document_references_from_session({document_id})


def _clear_document_references_from_session(document_ids: set[str]) -> None:
    """Drop filters and source-bearing messages for documents no longer in the index."""
    filters = st.session_state.get(CURRENT_FILTERS, {})
    if isinstance(filters, dict):
        filters["document_ids"] = [
            value for value in filters.get("document_ids", []) if value not in document_ids
        ]
        st.session_state[CURRENT_FILTERS] = filters
    st.session_state[CHAT_MESSAGES] = [
        message
        for message in _messages()
        if all(citation.document_id not in document_ids for citation in message.citations)
    ]


def _unload_chat_models(context: ApplicationContext) -> None:
    for provider in (context.chat_provider, context.fast_chat_provider):
        try:
            provider.unload()
        except Exception:
            continue


def _mark_model_activity(*, clear: bool = False) -> None:
    st.session_state[LAST_MODEL_ACTIVITY_AT] = None if clear else time.time()


def _cleanup_idle_models(context: ApplicationContext) -> None:
    mode = str(st.session_state.get(PERFORMANCE_MODE, "Balanced"))
    ttl = {
        "Fast": FAST_MODEL_IDLE_TTL_SECONDS,
        "Balanced": BALANCED_MODEL_IDLE_TTL_SECONDS,
        "Memory saver": MEMORY_SAVER_MODEL_IDLE_TTL_SECONDS,
    }.get(mode, BALANCED_MODEL_IDLE_TTL_SECONDS)
    last = st.session_state.get(LAST_MODEL_ACTIVITY_AT)
    if not isinstance(last, float):
        return
    if time.time() - last < ttl:
        return
    unload_local_models(context)
    _mark_model_activity(clear=True)


if __name__ == "__main__":
    main()
