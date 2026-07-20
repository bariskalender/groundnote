from __future__ import annotations

from groundnote.ui.state import (
    CURRENT_FILTERS,
    DEFAULT_SESSION_STATE,
    LAST_RAG_ANSWER,
    UPLOAD_IN_PROGRESS,
    clear_operation_flags,
    initialize_session_state,
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
