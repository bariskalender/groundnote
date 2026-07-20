"""Controlled Streamlit session-state initialization."""

from __future__ import annotations

from typing import Protocol


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
}


def initialize_session_state(state: SessionStateLike) -> None:
    """Initialize known keys without replacing existing session values."""
    for key, value in DEFAULT_SESSION_STATE.items():
        if key not in state:
            state[key] = _copy_default(value)


def clear_operation_flags(state: SessionStateLike) -> None:
    """Recover safe idle flags after an interrupted Streamlit operation."""
    state[UPLOAD_IN_PROGRESS] = False
    state[INDEXING_IN_PROGRESS] = False
    state[QUESTION_IN_PROGRESS] = False


def _copy_default(value: object) -> object:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, list):
        return list(value)
    return value
