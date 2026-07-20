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
UPLOAD_QUEUE = "upload_queue"
ACTIVE_UPLOAD_IDENTITY = "active_upload_identity"
COMPLETED_UPLOAD_IDENTITIES = "completed_upload_identities"
FAILED_UPLOAD_IDENTITIES = "failed_upload_identities"
UPLOAD_ITEMS = "upload_items"
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
    UPLOAD_QUEUE: [],
    ACTIVE_UPLOAD_IDENTITY: None,
    COMPLETED_UPLOAD_IDENTITIES: set(),
    FAILED_UPLOAD_IDENTITIES: set(),
    UPLOAD_ITEMS: {},
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
    state[ACTIVE_UPLOAD_IDENTITY] = None


class OperationStatus(StrEnum):
    """Lifecycle states for a recoverable UI operation."""

    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    STALE = "stale"


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
    if operation.operation_type == "upload":
        state[ACTIVE_UPLOAD_IDENTITY] = None


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
    state[ACTIVE_UPLOAD_IDENTITY] = None
    return True


def _copy_default(value: object) -> object:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, list):
        return list(value)
    if isinstance(value, set):
        return set(value)
    return value
