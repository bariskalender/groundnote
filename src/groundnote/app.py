"""GroundNote Streamlit application entrypoint."""

from __future__ import annotations

import hashlib
import os
import time
from uuid import uuid4

import streamlit as st

from groundnote import __version__
from groundnote.domain import DocumentStatus, SupportedFileType
from groundnote.performance import IndexingDiagnostics, IndexingProgress, IndexingStage
from groundnote.ui import ApplicationContext, build_application_context, unload_local_models
from groundnote.ui.components.notices import render_message
from groundnote.ui.components.upload import render_upload_control
from groundnote.ui.errors import DatabaseBootstrapError, map_exception, safe_failure_message
from groundnote.ui.formatting import format_duration, format_file_type, safe_filename
from groundnote.ui.foundry_status import FoundryStatusKind, localized_foundry_status
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
    LAST_UPLOAD_RESULT,
    PENDING_CLEAR_DOCUMENTS,
    PENDING_DELETE_DOCUMENT_ID,
    PERFORMANCE_MODE,
    SHOW_DEBUG_DETAILS,
    UI_LANGUAGE,
    FlashNotice,
    FlashSeverity,
    OperationState,
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
    register_selected_upload,
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
        new_chat_allowed = can_start_new_chat(st.session_state) and not _indexing_active(context)
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
        document_operation_active = operation_is_active(
            st.session_state.get(ACTIVE_OPERATION)
        ) or _indexing_active(context)
        uploaded = render_upload_control(
            context.settings.maximum_upload_size_mb,
            language,
            disabled=document_operation_active,
            key=upload_widget_key(st.session_state),
        )
        try:
            registration = register_selected_upload(
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

        if registration is not None:
            if registration.blocked:
                st.info(t("operation_busy_upload", language))
                reset_upload_widget(st.session_state)
            if registration.selection is not None:
                _notice(processing_notice, t("validating_upload", language))
                _process_selected_upload(context, registration.selection, language)
            _clear_notice(processing_notice)

        _render_document_list(context, language)
        _render_latest_indexing_diagnostics(language)
        _render_sources_sidebar(context, language)
        _render_foundry_status(context, language)
        st.caption(t("local_notice", language))


def _process_selected_upload(
    context: ApplicationContext,
    selection: SelectedUpload,
    language: str,
) -> None:
    if not _can_start_operation(context):
        st.info(t("operation_busy_upload", language))
        return
    _unload_chat_models(context)
    operation = begin_operation(
        st.session_state,
        "upload",
        file_identity=selection.identity,
    )
    succeeded = False
    rerun = False
    with st.status(
        f"{t('validating_upload', language)}: {selection.filename}",
        expanded=False,
    ) as status:

        def show_stage(stage: UploadStage) -> None:
            status.write(_upload_stage_label(stage, language))

        last_progress: list[IndexingProgress | None] = [None]

        def show_progress(progress: IndexingProgress) -> None:
            last_progress[0] = progress
            status.write(_indexing_progress_label(progress, language))

        data: bytes | None = None
        try:
            data = selection.data
            outcome = context.document_workflow.process_and_index(
                original_filename=selection.filename,
                data=data,
                on_stage=show_stage,
                on_progress=show_progress,
                precomputed_sha256=selection.content_sha256,
            )
            st.session_state[LAST_UPLOAD_RESULT] = outcome
            terminal_label = (
                t("duplicate", language)
                if outcome.kind is UploadOutcomeKind.DUPLICATE
                else t("ready", language)
            )
            status.update(
                label=(
                    f"{terminal_label}: "
                    f"{selection.filename} · {format_duration(outcome.duration_ms)}"
                ),
                state="complete",
                expanded=False,
            )
            succeeded = True
            set_flash_notice(
                st.session_state,
                FlashNotice(message=terminal_label, severity=FlashSeverity.SUCCESS),
            )
            _mark_model_activity()
            rerun = True
        except Exception as exc:
            original_error = exc
            message = safe_failure_message(
                original_error,
                logger=get_logger(__name__),
                event="ui_document_operation_failed",
                language=language,
            )
            failed_stage = last_progress[0].stage if last_progress[0] is not None else None
            status.update(
                label=_indexing_failure_label(selection.filename, failed_stage, language),
                state="error",
                expanded=False,
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
            rerun = True
        finally:
            data = None
            end_operation(st.session_state, operation, succeeded=succeeded)
            reset_upload_widget(st.session_state)
    if rerun:
        st.rerun()


def _render_document_list(
    context: ApplicationContext,
    language: str,
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

    if not documents:
        st.caption(t("no_documents", language))
        return

    if documents:
        _render_clear_all_documents(context, documents, language)
        st.caption(t("indexed_documents", language))

    for document in documents[:20]:
        _render_document_row(context, document, language)


def _render_document_row(
    context: ApplicationContext,
    document: DocumentSummary,
    language: str,
) -> None:
    filename_column, status_column, action_column = st.columns([6, 3, 2])
    filename_column.caption(f"📄 {safe_filename(document.original_filename)}")
    status_column.caption(_document_status_label(document.status, language))
    if document.status == DocumentStatus.FAILED:
        identity = f"document-{document.document_id}"
        if action_column.button(t("retry", language), key=f"retry-{identity}"):
            _retry_index_document(context, document, language)


def _retry_index_document(
    context: ApplicationContext,
    document: DocumentSummary,
    language: str,
) -> None:
    if not _can_start_operation(context):
        st.info(t("operation_busy_indexing", language))
        return
    identity = f"document-{document.document_id}"
    operation = begin_operation(st.session_state, "upload", file_identity=identity)
    succeeded = False
    try:
        context.indexing_service.index_document(
            document.document_id,
            force_reindex=document.status == DocumentStatus.FAILED,
        )
        succeeded = True
    except Exception as exc:
        message = safe_failure_message(
            exc,
            logger=get_logger(__name__),
            event="ui_document_retry_failed",
            language=language,
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
    status = localized_foundry_status(context.foundry_status_service.check(), language)
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
    current_operation = st.session_state.get(ACTIVE_OPERATION)
    indexing_active = _indexing_active(context)
    active = operation_is_active(current_operation) or indexing_active
    if active:
        st.caption(
            t("chat_busy_indexing", language)
            if indexing_active
            else _chat_busy_message(current_operation, language)
        )
    prompt = st.chat_input(
        t("ask_placeholder", language),
        max_chars=context.settings.rag_max_query_characters,
        disabled=active,
    )
    if prompt:
        if not _can_start_operation(context):
            st.info(_chat_busy_message(st.session_state.get(ACTIVE_OPERATION), language))
            return
        _answer_prompt(context, prompt, language)


def _answer_prompt(context: ApplicationContext, prompt: str, language: str) -> None:
    if not _can_start_operation(context):
        st.info(_chat_busy_message(st.session_state.get(ACTIVE_OPERATION), language))
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


def _upload_stage_label(stage: UploadStage, language: str) -> str:
    key = {
        UploadStage.SAVING: "validating_upload",
        UploadStage.PROCESSING: "processing",
        UploadStage.INDEXING: "indexing",
        UploadStage.FINALIZING: "indexing",
        UploadStage.READY: "ready",
    }[stage]
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
    language: str,
) -> None:
    """Render one responsive card with vertically stacked full-width actions."""
    with st.container(border=True):
        document_action_busy = not _can_start_operation(context)
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
            identity = f"document-{document.document_id}"
            if st.button(
                t("retry", language),
                key=f"retry-{identity}",
                use_container_width=True,
                disabled=document_action_busy,
            ):
                _retry_index_document(context, document, language)


def _delete_document(
    context: ApplicationContext,
    document: DocumentSummary,
    language: str,
) -> None:
    if not _can_start_operation(context):
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
    if not _can_start_operation(context):
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
            refreshed = context.document_workflow.reindex_document(
                document.document_id,
                on_progress=lambda progress: status.write(
                    _indexing_progress_label(progress, language)
                ),
            )
            duration_ms = (
                refreshed.indexing_diagnostics.total_duration_ms
                if refreshed.indexing_diagnostics is not None
                else None
            )
            status.update(
                label=(
                    f"{t('ready', language)} · {format_duration(duration_ms)}"
                    if duration_ms is not None
                    else t("ready", language)
                ),
                state="complete",
                expanded=False,
            )
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
            disabled=not _can_start_operation(context),
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
        disabled=not _can_start_operation(context),
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
    if not _can_start_operation(context):
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


def _render_latest_indexing_diagnostics(language: str) -> None:
    if not st.session_state.get(SHOW_DEBUG_DETAILS):
        return
    outcome = st.session_state.get(LAST_UPLOAD_RESULT)
    diagnostics = getattr(outcome, "diagnostics", None)
    if not isinstance(diagnostics, IndexingDiagnostics):
        return
    with st.expander(t("indexing_diagnostics", language), expanded=False):
        st.caption(
            t("indexing_diagnostics_summary", language).format(
                duration=format_duration(diagnostics.total_duration_ms),
                chunks=diagnostics.chunk_count,
                batches=diagnostics.embedding_batch_count,
            )
        )
        st.caption(
            t("indexing_model_usage", language).format(
                load_duration=format_duration(diagnostics.model_load_duration_ms),
                reuse=t("yes", language) if diagnostics.model_reused else t("no", language),
            )
        )
        if diagnostics.peak_process_rss_mb is not None:
            st.caption(
                t("indexing_peak_memory", language).format(memory=diagnostics.peak_process_rss_mb)
            )
        for stage, duration_ms in diagnostics.stage_durations_ms.items():
            st.caption(
                f"{_indexing_stage_label(IndexingStage(stage), language)}: "
                f"{format_duration(duration_ms)}"
            )


def _indexing_progress_label(progress: IndexingProgress, language: str) -> str:
    label = _indexing_stage_label(progress.stage, language)
    if progress.completed_units is not None and progress.total_units is not None:
        label = f"{label}: {progress.completed_units} / {progress.total_units}"
    return f"{label} · {format_duration(progress.elapsed_ms)}"


def _indexing_stage_label(stage: IndexingStage, language: str) -> str:
    return t(f"index_stage_{stage.value}", language)


def _indexing_failure_label(
    filename: str,
    stage: IndexingStage | None,
    language: str,
) -> str:
    safe_name = safe_filename(filename)
    if stage is None:
        return f"{t('failed', language)}: {safe_name}"
    return t("indexing_failed_at", language).format(
        filename=safe_name,
        stage=_indexing_stage_label(stage, language),
    )


def _chat_busy_message(operation: object, language: str) -> str:
    if isinstance(operation, OperationState) and operation.operation_type in {"upload", "reindex"}:
        return t("chat_busy_indexing", language)
    return t("operation_busy_question", language)


def _indexing_active(context: ApplicationContext) -> bool:
    """Use process ownership, not browser session state, for active indexing."""
    return context.indexing_registry.is_active()


def _can_start_operation(context: ApplicationContext) -> bool:
    """Block UI work while either this session or another refreshed session is indexing."""
    return can_start_operation(st.session_state) and not _indexing_active(context)


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
