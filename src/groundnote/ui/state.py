"""Controlled Streamlit session-state initialization."""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import uuid4


class SessionStateLike(Protocol):
    """Small state contract shared by Streamlit and plain dictionaries."""

    def __contains__(self, key: object) -> bool: ...
    def __setitem__(self, key: str, value: object) -> None: ...


ACTIVE_PAGE = "active_page"
LAST_UPLOADED_DOCUMENT_ID = "last_uploaded_document_id"
LAST_UPLOAD_RESULT = "last_upload_result"
UPLOAD_IN_PROGRESS = "upload_in_progress"
INDEXING_IN_PROGRESS = "indexing_in_progress"
LAST_INDEXING_RESULT = "last_indexing_result"
LAST_QUESTION = "last_question"
LAST_RAG_ANSWER = "last_rag_answer"
CURRENT_FILTERS = "current_filters"
UI_NOTIFICATIONS = "ui_notifications"
QUESTION_IN_PROGRESS = "question_in_progress"
ACTIVE_OPERATION = "active_operation"
CHAT_MESSAGES = "chat_messages"
UI_LANGUAGE = "ui_language"
PERFORMANCE_MODE = "performance_mode"
ANSWER_LANGUAGE = "answer_language"
LAST_SUBMITTED_QUESTION = "last_submitted_question"
LAST_UPLOAD_SELECTION_TOKEN = "last_upload_selection_token"
SHOW_DEBUG_DETAILS = "show_debug_details"
PENDING_DELETE_DOCUMENT_ID = "pending_delete_document_id"
PENDING_CLEAR_DOCUMENTS = "pending_clear_documents"
LAST_MODEL_ACTIVITY_AT = "last_model_activity_at"
FLASH_NOTICE = "flash_notice"
UPLOAD_WIDGET_REVISION = "upload_widget_revision"
OPERATION_STALE_SECONDS = 600.0

DEFAULT_SESSION_STATE: dict[str, object] = {
    ACTIVE_PAGE: "Documents",
    LAST_UPLOADED_DOCUMENT_ID: None,
    LAST_UPLOAD_RESULT: None,
    UPLOAD_IN_PROGRESS: False,
    INDEXING_IN_PROGRESS: False,
    LAST_INDEXING_RESULT: None,
    LAST_QUESTION: None,
    LAST_RAG_ANSWER: None,
    CURRENT_FILTERS: {"document_ids": [], "file_types": []},
    UI_NOTIFICATIONS: [],
    QUESTION_IN_PROGRESS: False,
    ACTIVE_OPERATION: None,
    CHAT_MESSAGES: [],
    UI_LANGUAGE: "en",
    PERFORMANCE_MODE: "Balanced",
    ANSWER_LANGUAGE: "auto",
    LAST_SUBMITTED_QUESTION: None,
    LAST_UPLOAD_SELECTION_TOKEN: None,
    SHOW_DEBUG_DETAILS: False,
    PENDING_DELETE_DOCUMENT_ID: None,
    PENDING_CLEAR_DOCUMENTS: False,
    LAST_MODEL_ACTIVITY_AT: None,
    FLASH_NOTICE: None,
    UPLOAD_WIDGET_REVISION: 0,
}


def initialize_session_state(state: SessionStateLike) -> None:
    """Initialize known keys without replacing existing session values."""
    for key, value in DEFAULT_SESSION_STATE.items():
        if key not in state:
            state[key] = _copy_default(value)
    recover_stale_operation(state)


def clear_operation_flags(state: SessionStateLike) -> None:
    """Recover safe idle flags after an interrupted Streamlit operation."""
    state[UPLOAD_IN_PROGRESS] = False
    state[INDEXING_IN_PROGRESS] = False
    state[QUESTION_IN_PROGRESS] = False
    state[ACTIVE_OPERATION] = None


class OperationStatus(StrEnum):
    """Lifecycle states for a recoverable UI operation."""

    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    STALE = "stale"


class FlashSeverity(StrEnum):
    """Supported one-time notice styles across a Streamlit rerun."""

    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class FlashNotice:
    """Privacy-safe one-time feedback rendered after a Streamlit rerun."""

    message: str
    severity: FlashSeverity
    title: str | None = None
    remediation: str | None = None


@dataclass(frozen=True)
class OperationState:
    """Recoverable Streamlit operation state."""

    operation_id: str
    operation_type: str
    started_at: float
    file_identity: str | None = None
    status: OperationStatus = OperationStatus.ACTIVE
    completed_at: float | None = None

    @property
    def active(self) -> bool:
        """Compatibility property for UI callers."""
        return self.status == OperationStatus.ACTIVE


def operation_is_active(state: object) -> bool:
    """Return true only for a non-stale active operation object."""
    if not isinstance(state, OperationState):
        return False
    return state.active and (time.time() - state.started_at) <= OPERATION_STALE_SECONDS


def can_start_operation(state: SessionStateLike) -> bool:
    """Return false while a non-stale UI operation is already active."""
    current = getattr(state, "get", lambda _key, _default=None: _default)(
        ACTIVE_OPERATION,
        None,
    )
    return not operation_is_active(current)


def can_start_new_chat(state: SessionStateLike) -> bool:
    """A new chat never interrupts a database or answer operation."""
    return can_start_operation(state)


def clear_chat_messages(state: SessionStateLike) -> None:
    """Clear in-memory conversation messages without changing documents or settings."""
    state[CHAT_MESSAGES] = []


def set_flash_notice(state: SessionStateLike, notice: FlashNotice) -> None:
    """Store safe feedback until the next completed render consumes it."""
    state[FLASH_NOTICE] = notice


def pop_flash_notice(state: SessionStateLike) -> FlashNotice | None:
    """Return and clear one pending notice so it is rendered exactly once."""
    current = getattr(state, "get", lambda _key, _default=None: _default)(FLASH_NOTICE, None)
    state[FLASH_NOTICE] = None
    return current if isinstance(current, FlashNotice) else None


def upload_widget_key(state: SessionStateLike) -> str:
    """Return the current stable uploader key without exposing selected file data."""
    revision = getattr(state, "get", lambda _key, _default=None: _default)(
        UPLOAD_WIDGET_REVISION, 0
    )
    safe_revision = revision if isinstance(revision, int) and revision >= 0 else 0
    return f"groundnote-upload-{safe_revision}"


def reset_upload_widget(state: SessionStateLike) -> None:
    """Advance the uploader key and release the terminal single-selection token."""
    current = getattr(state, "get", lambda _key, _default=None: _default)(UPLOAD_WIDGET_REVISION, 0)
    revision = current if isinstance(current, int) and current >= 0 else 0
    state[UPLOAD_WIDGET_REVISION] = revision + 1
    state[LAST_UPLOAD_SELECTION_TOKEN] = None


def begin_operation(
    state: SessionStateLike,
    operation_type: str,
    *,
    file_identity: str | None = None,
) -> OperationState:
    """Start one recoverable operation."""
    operation = OperationState(
        operation_id=str(uuid4()),
        operation_type=operation_type,
        started_at=time.time(),
        file_identity=file_identity,
    )
    state[ACTIVE_OPERATION] = operation
    if operation_type == "upload":
        state[UPLOAD_IN_PROGRESS] = True
    if operation_type == "question":
        state[QUESTION_IN_PROGRESS] = True
    return operation


def end_operation(
    state: SessionStateLike,
    operation: OperationState,
    *,
    succeeded: bool = True,
) -> None:
    """Release the active operation if it still matches this run."""
    current = getattr(state, "get", lambda _key, _default=None: _default)(
        ACTIVE_OPERATION,
        None,
    )
    if isinstance(current, OperationState) and current.operation_id == operation.operation_id:
        state[ACTIVE_OPERATION] = OperationState(
            operation_id=operation.operation_id,
            operation_type=operation.operation_type,
            started_at=operation.started_at,
            file_identity=operation.file_identity,
            status=OperationStatus.COMPLETED if succeeded else OperationStatus.FAILED,
            completed_at=time.time(),
        )
    state[UPLOAD_IN_PROGRESS] = False
    state[INDEXING_IN_PROGRESS] = False
    state[QUESTION_IN_PROGRESS] = False


def recover_stale_operation(state: SessionStateLike) -> bool:
    """Release an interrupted operation after its bounded stale interval."""
    current = getattr(state, "get", lambda _key, _default=None: _default)(
        ACTIVE_OPERATION,
        None,
    )
    if not isinstance(current, OperationState):
        return False
    if current.status != OperationStatus.ACTIVE:
        return False
    if (time.time() - current.started_at) <= OPERATION_STALE_SECONDS:
        return False
    state[ACTIVE_OPERATION] = OperationState(
        operation_id=current.operation_id,
        operation_type=current.operation_type,
        started_at=current.started_at,
        file_identity=current.file_identity,
        status=OperationStatus.STALE,
        completed_at=time.time(),
    )
    state[UPLOAD_IN_PROGRESS] = False
    state[INDEXING_IN_PROGRESS] = False
    state[QUESTION_IN_PROGRESS] = False
    return True


def _copy_default(value: object) -> object:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, list):
        return list(value)
    if isinstance(value, set):
        return set(value)
    return value
