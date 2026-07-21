from __future__ import annotations

from dataclasses import dataclass

from groundnote.ui.errors import map_exception
from groundnote.ui.state import (
    PERFORMANCE_MODE,
    UI_LANGUAGE,
    UPLOAD_ITEMS,
    UPLOAD_QUEUE,
    initialize_session_state,
)
from groundnote.ui.uploads import (
    UploadStatus,
    complete_upload,
    fail_upload,
    queue_retry,
    register_selected_uploads,
    start_upload,
    upload_items,
)


@dataclass
class FakeUpload:
    name: str
    data: bytes

    def getvalue(self) -> bytes:
        return self.data


def test_selected_files_queue_automatically_once_across_reruns() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    files = [FakeUpload("one.txt", b"one"), FakeUpload("two.txt", b"two")]

    first = register_selected_uploads(state, files)
    for index, selection in enumerate(first.queued):
        start_upload(state, selection.identity)
        complete_upload(
            state,
            selection.identity,
            status=UploadStatus.READY,
            document_id=f"doc-{index}",
        )
    state[UI_LANGUAGE] = "tr"
    state[PERFORMANCE_MODE] = "Fast"
    rerun = register_selected_uploads(state, files)

    assert len(first.queued) == 2
    assert rerun.queued == ()
    assert state[UPLOAD_QUEUE] == []
    assert all(item.status is UploadStatus.READY for item in upload_items(state))


def test_second_batch_keeps_completed_first_batch_and_duplicate_selection_is_skipped() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    first_file = FakeUpload("one.txt", b"one")
    first = register_selected_uploads(state, [first_file])
    first_selection = first.queued[0]
    start_upload(state, first_selection.identity)
    complete_upload(
        state,
        first_selection.identity,
        status=UploadStatus.READY,
        document_id="doc-one",
    )

    second = register_selected_uploads(
        state,
        [first_file, FakeUpload("two.txt", b"two"), FakeUpload("two.txt", b"two")],
    )

    assert len(second.queued) == 1
    assert second.queued[0].filename == "two.txt"
    assert any(item.document_id == "doc-one" for item in upload_items(state))


def test_failed_file_is_isolated_retryable_and_state_keeps_no_bytes() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    registration = register_selected_uploads(
        state,
        [FakeUpload("corrupt.pdf", b"broken"), FakeUpload("valid.txt", b"valid")],
    )
    failed_selection, valid_selection = registration.queued

    start_upload(state, failed_selection.identity)
    fail_upload(
        state,
        failed_selection.identity,
        message=map_exception(RuntimeError("private parser detail")),
    )
    start_upload(state, valid_selection.identity)
    complete_upload(
        state,
        valid_selection.identity,
        status=UploadStatus.READY,
        document_id="doc-valid",
    )
    retried = queue_retry(state, failed_selection.identity)

    assert retried.status is UploadStatus.WAITING
    assert state[UPLOAD_QUEUE] == [failed_selection.identity]
    assert not _contains_bytes(state)
    assert all(not hasattr(item, "data") for item in state[UPLOAD_ITEMS].values())


def test_second_upload_is_rejected_without_queueing_while_operation_is_busy() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    second = FakeUpload("second.txt", b"second private content")

    registration = register_selected_uploads(state, [second], block_new=True)

    assert registration.queued == ()
    assert registration.selected == {}
    assert registration.blocked_count == 1
    assert state[UPLOAD_QUEUE] == []
    assert state[UPLOAD_ITEMS] == {}
    assert not _contains_bytes(state)


def test_waiting_upload_recovers_on_next_idle_rerun_instead_of_staying_locked() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    upload = FakeUpload("waiting.txt", b"waiting")
    first = register_selected_uploads(state, [upload])
    identity = first.queued[0].identity

    rerun = register_selected_uploads(state, [upload])

    assert [selection.identity for selection in rerun.queued] == [identity]
    assert state[UPLOAD_QUEUE] == [identity]


def _contains_bytes(value: object) -> bool:
    if isinstance(value, bytes):
        return True
    if isinstance(value, dict):
        return any(_contains_bytes(key) or _contains_bytes(item) for key, item in value.items())
    if isinstance(value, (list, tuple, set)):
        return any(_contains_bytes(item) for item in value)
    return False
