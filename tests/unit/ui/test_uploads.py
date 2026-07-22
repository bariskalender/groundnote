from __future__ import annotations

import hashlib

from groundnote.ui.state import LAST_UPLOAD_SELECTION_TOKEN, initialize_session_state
from groundnote.ui.uploads import register_selected_upload, upload_identity


class UploadedFile:
    def __init__(self, name: str, data: bytes, *, file_id: str) -> None:
        self.name = name
        self.size = len(data)
        self.type = "text/plain"
        self.file_id = file_id
        self._data = data
        self.read_count = 0

    def getvalue(self) -> bytes:
        self.read_count += 1
        return self._data


def test_one_file_is_read_and_hashed_once_without_retaining_bytes() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    uploaded = UploadedFile("study notes.txt", b"local evidence", file_id="one")

    registration = register_selected_upload(state, uploaded)

    assert registration.blocked is False
    assert registration.selection is not None
    assert registration.selection.filename == "study notes.txt"
    assert registration.selection.content_sha256 == hashlib.sha256(b"local evidence").hexdigest()
    assert uploaded.read_count == 1
    assert all(not isinstance(value, bytes) for value in state.values())


def test_same_browser_selection_is_not_registered_again_on_rerun() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    uploaded = UploadedFile("rerun.txt", b"one operation", file_id="stable")

    first = register_selected_upload(state, uploaded)
    rerun = register_selected_upload(state, uploaded)

    assert first.selection is not None
    assert rerun.selection is None
    assert uploaded.read_count == 1


def test_new_selection_can_follow_a_completed_single_selection() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    first = UploadedFile("one.txt", b"one", file_id="one")
    second = UploadedFile("two.txt", b"two", file_id="two")

    assert register_selected_upload(state, first).selection is not None
    registration = register_selected_upload(state, second)

    assert registration.selection is not None
    assert registration.selection.filename == "two.txt"
    assert first.read_count == 1
    assert second.read_count == 1


def test_active_indexing_blocks_selection_before_bytes_enter_state() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    uploaded = UploadedFile("blocked.txt", b"must not be read", file_id="blocked")

    registration = register_selected_upload(state, uploaded, block_new=True)

    assert registration.blocked is True
    assert registration.selection is None
    assert uploaded.read_count == 0
    assert state[LAST_UPLOAD_SELECTION_TOKEN] is None


def test_unicode_and_spaced_filename_has_stable_identity() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    data = "yerel çalışma notu".encode()
    uploaded = UploadedFile("Çalışma Notları 1.txt", data, file_id="unicode")

    registration = register_selected_upload(state, uploaded)

    assert registration.selection is not None
    assert registration.selection.identity == upload_identity("Çalışma Notları 1.txt", data)


def test_single_upload_state_contains_no_queue_structures() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)

    assert "upload_queue" not in state
    assert "upload_items" not in state
    assert "completed_upload_identities" not in state
    assert "failed_upload_identities" not in state
