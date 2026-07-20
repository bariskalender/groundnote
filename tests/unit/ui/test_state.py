from __future__ import annotations

import time

from groundnote.ui.state import (
    ACTIVE_OPERATION,
    CHAT_MESSAGES,
    CURRENT_FILTERS,
    DEFAULT_SESSION_STATE,
    LAST_RAG_ANSWER,
    OPERATION_STALE_SECONDS,
    UPLOAD_IN_PROGRESS,
    OperationState,
    OperationStatus,
    begin_operation,
    clear_operation_flags,
    end_operation,
    initialize_session_state,
    operation_is_active,
    recover_stale_operation,
)


def test_session_state_defaults_are_deterministic() -> None:
    state: dict[str, object] = {}

    initialize_session_state(state)

    assert set(state) == set(DEFAULT_SESSION_STATE)
    assert state[UPLOAD_IN_PROGRESS] is False
    assert state[LAST_RAG_ANSWER] is None
    assert state[CURRENT_FILTERS] == {"document_ids": [], "file_types": []}


def test_session_state_preserves_existing_values_and_copies_containers() -> None:
    state: dict[str, object] = {LAST_RAG_ANSWER: "latest-safe-answer"}

    initialize_session_state(state)
    filters = state[CURRENT_FILTERS]

    assert state[LAST_RAG_ANSWER] == "latest-safe-answer"
    assert filters == {"document_ids": [], "file_types": []}
    assert filters is not DEFAULT_SESSION_STATE[CURRENT_FILTERS]


def test_operation_flags_can_be_recovered_without_touching_results() -> None:
    state: dict[str, object] = {LAST_RAG_ANSWER: "answer", UPLOAD_IN_PROGRESS: True}
    initialize_session_state(state)

    clear_operation_flags(state)

    assert state[UPLOAD_IN_PROGRESS] is False
    assert state[LAST_RAG_ANSWER] == "answer"
    assert not any(isinstance(value, bytes) for value in state.values())


def test_operation_object_starts_and_releases_without_stale_boolean_lock() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)

    operation = begin_operation(state, "question")
    assert operation_is_active(state[ACTIVE_OPERATION]) is True

    end_operation(state, operation)

    assert operation_is_active(state[ACTIVE_OPERATION]) is False
    assert state[UPLOAD_IN_PROGRESS] is False


def test_new_chat_state_can_clear_messages_without_touching_filters() -> None:
    state: dict[str, object] = {CHAT_MESSAGES: ["message"], CURRENT_FILTERS: {"document_ids": []}}
    initialize_session_state(state)

    state[CHAT_MESSAGES] = []

    assert state[CHAT_MESSAGES] == []
    assert state[CURRENT_FILTERS] == {"document_ids": []}


def test_stale_operation_is_detected_and_released() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    state[ACTIVE_OPERATION] = OperationState(
        operation_id="stale-operation",
        operation_type="upload",
        started_at=time.time() - OPERATION_STALE_SECONDS - 1,
        file_identity="file-1",
    )
    state[UPLOAD_IN_PROGRESS] = True

    recovered = recover_stale_operation(state)

    assert recovered is True
    assert state[UPLOAD_IN_PROGRESS] is False
    operation = state[ACTIVE_OPERATION]
    assert isinstance(operation, OperationState)
    assert operation.status is OperationStatus.STALE
    assert operation_is_active(state[ACTIVE_OPERATION]) is False
