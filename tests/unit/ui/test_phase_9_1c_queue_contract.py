from __future__ import annotations

from dataclasses import dataclass

import pytest

from groundnote.ui.errors import map_exception
from groundnote.ui.state import (
    ACTIVE_UPLOAD_IDENTITY,
    CHAT_MESSAGES,
    begin_operation,
    clear_chat_messages,
    end_operation,
    initialize_session_state,
    reset_upload_widget,
)
from groundnote.ui.uploads import (
    UploadStatus,
    cancel_waiting_upload,
    clear_finished_uploads,
    complete_upload,
    fail_upload,
    get_upload_item,
    next_waiting_upload,
    queue_retry,
    register_selected_uploads,
    retained_upload_bytes,
    start_upload,
    summarize_upload_queue,
    update_upload_status,
    upload_items,
)


@dataclass
class FakeUpload:
    name: str
    data: bytes

    @property
    def size(self) -> int:
        return len(self.data)

    def getvalue(self) -> bytes:
        return self.data


def test_waiting_queue_owns_one_bounded_buffer_across_a_rerun() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    upload = FakeUpload("lecture notes.txt", b"private waiting bytes")

    first = register_selected_uploads(state, [upload])
    rerun = register_selected_uploads(state, [])

    assert len(first.queued) == 1
    assert rerun.queued == first.queued
    assert upload_items(state)[0].data is upload.data


def test_file_count_limit_is_checked_before_reading_upload_bytes() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    files = [FakeUpload("one.txt", b"one"), FakeUpload("two.txt", b"two")]

    with pytest.raises(ValueError, match="file count"):
        register_selected_uploads(
            state,
            files,
            maximum_file_count=1,
            maximum_total_bytes=100,
        )


def test_file_count_limit_includes_existing_waiting_items() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    register_selected_uploads(
        state,
        [FakeUpload("one.txt", b"one")],
        maximum_file_count=2,
    )

    with pytest.raises(ValueError, match="file count|queue exceeds"):
        register_selected_uploads(
            state,
            [FakeUpload("two.txt", b"two"), FakeUpload("three.txt", b"three")],
            maximum_file_count=2,
        )

    assert [item.filename for item in upload_items(state)] == ["one.txt"]


def test_total_size_limit_rejects_the_submission_without_queue_mutation() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)

    with pytest.raises(ValueError, match="total size"):
        register_selected_uploads(
            state,
            [FakeUpload("large.txt", b"12345")],
            maximum_file_count=10,
            maximum_total_bytes=4,
        )

    assert upload_items(state) == []


@pytest.mark.parametrize("count", [2, 3])
def test_multiple_selection_preserves_order_and_safe_metadata(count: int) -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    files = [FakeUpload(f"ders {index}.txt", f"note-{index}".encode()) for index in range(count)]

    registration = register_selected_uploads(state, files)
    items = upload_items(state)

    assert registration.accepted_count == count
    assert [item.filename for item in items] == [file.name for file in files]
    assert [item.sequence for item in items] == list(range(count))
    assert all(item.status is UploadStatus.WAITING for item in items)
    assert all(len(item.content_sha256) == 64 for item in items)


def test_mixed_types_unicode_and_spaces_remain_independent() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)

    register_selected_uploads(
        state,
        [
            FakeUpload("Türkçe ders notu.md", b"markdown"),
            FakeUpload("lecture notes.docx", b"docx"),
            FakeUpload("week 1.pdf", b"pdf"),
        ],
    )

    assert [(item.filename, item.file_type) for item in upload_items(state)] == [
        ("Türkçe ders notu.md", "markdown"),
        ("lecture notes.docx", "docx"),
        ("week 1.pdf", "pdf"),
    ]


def test_only_one_item_is_active_and_transitions_are_guarded() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    registration = register_selected_uploads(
        state,
        [FakeUpload("one.txt", b"one"), FakeUpload("two.txt", b"two")],
    )
    first, second = registration.queued

    with pytest.raises(ValueError, match="not active"):
        complete_upload(state, first, status=UploadStatus.READY, document_id="doc-one")
    start_upload(state, first)
    with pytest.raises(ValueError, match="already active"):
        start_upload(state, second)
    update_upload_status(
        state,
        first,
        UploadStatus.EMBEDDING,
        completed_units=2,
        total_units=5,
    )
    complete_upload(state, first, status=UploadStatus.READY, document_id="doc-one")

    assert state[ACTIVE_UPLOAD_IDENTITY] is None
    assert get_upload_item(state, first).data is None
    assert next_waiting_upload(state).identity == second  # type: ignore[union-attr]


def test_failure_and_duplicate_release_bytes_and_do_not_block_next_item() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    registration = register_selected_uploads(
        state,
        [
            FakeUpload("bad.pdf", b"bad"),
            FakeUpload("duplicate.txt", b"duplicate"),
            FakeUpload("valid.txt", b"valid"),
        ],
    )
    failed_id, duplicate_id, valid_id = registration.queued

    start_upload(state, failed_id)
    fail_upload(state, failed_id, message=map_exception(RuntimeError("private detail")))
    start_upload(state, duplicate_id)
    complete_upload(
        state,
        duplicate_id,
        status=UploadStatus.DUPLICATE,
        document_id="existing",
    )
    start_upload(state, valid_id)
    complete_upload(state, valid_id, status=UploadStatus.READY, document_id="valid")

    assert retained_upload_bytes(state) == 0
    assert [item.status for item in upload_items(state)] == [
        UploadStatus.FAILED,
        UploadStatus.DUPLICATE,
        UploadStatus.READY,
    ]


def test_waiting_cancel_releases_bytes_without_affecting_other_items() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    first, second = register_selected_uploads(
        state,
        [FakeUpload("one.txt", b"one"), FakeUpload("two.txt", b"two")],
    ).queued

    cancelled = cancel_waiting_upload(state, second)

    assert cancelled.status is UploadStatus.CANCELLED
    assert cancelled.data is None
    assert next_waiting_upload(state).identity == first  # type: ignore[union-attr]
    with pytest.raises(ValueError, match="waiting"):
        cancel_waiting_upload(state, second)


def test_persisted_failure_retry_is_explicit_and_never_duplicated() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    identity = register_selected_uploads(state, [FakeUpload("retry.txt", b"retry")]).queued[0]
    start_upload(state, identity)
    fail_upload(
        state,
        identity,
        message=map_exception(RuntimeError("private detail")),
        document_id="document-id",
    )

    retried = queue_retry(state, identity)

    assert retried.status is UploadStatus.WAITING
    assert retried.data is None
    with pytest.raises(ValueError, match="already waiting"):
        queue_retry(state, identity)


def test_interrupted_persisted_item_is_not_ready_and_can_be_retried() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    identity = register_selected_uploads(
        state,
        [FakeUpload("interrupted.txt", b"interrupted")],
    ).queued[0]
    start_upload(state, identity)

    interrupted = fail_upload(
        state,
        identity,
        message=map_exception(RuntimeError("Indexing was interrupted.")),
        document_id="failed-document-id",
        interrupted=True,
    )

    assert interrupted.status is UploadStatus.INTERRUPTED
    assert interrupted.retry_available is True
    assert interrupted.data is None
    assert summarize_upload_queue(
        state,
        duration_ms=1.0,
        identities=[identity],
    ).finished
    assert queue_retry(state, identity).status is UploadStatus.WAITING


def test_completed_submission_does_not_rerun_after_ui_changes_or_widget_reset() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    upload = FakeUpload("stable.txt", b"stable")
    identity = register_selected_uploads(state, [upload]).queued[0]
    start_upload(state, identity)
    complete_upload(state, identity, status=UploadStatus.READY, document_id="doc")
    state[CHAT_MESSAGES] = ["session message"]
    clear_chat_messages(state)

    same_widget = register_selected_uploads(state, [upload])
    reset_upload_widget(state)
    reset_widget = register_selected_uploads(state, [upload])

    assert same_widget.queued == ()
    assert reset_widget.queued == ()
    assert get_upload_item(state, identity).status is UploadStatus.READY


def test_clear_finished_results_removes_only_terminal_metadata() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    ready_id, waiting_id = register_selected_uploads(
        state,
        [FakeUpload("ready.txt", b"ready"), FakeUpload("waiting.txt", b"waiting")],
    ).queued
    start_upload(state, ready_id)
    complete_upload(state, ready_id, status=UploadStatus.READY, document_id="doc")

    removed = clear_finished_uploads(state)

    assert removed == 1
    assert [item.identity for item in upload_items(state)] == [waiting_id]
    assert retained_upload_bytes(state) == len(b"waiting")


def test_queue_summary_and_global_operation_finish_only_after_every_item() -> None:
    state: dict[str, object] = {}
    initialize_session_state(state)
    identities = list(
        register_selected_uploads(
            state,
            [FakeUpload("one.txt", b"one"), FakeUpload("two.txt", b"two")],
        ).queued
    )
    operation = begin_operation(state, "upload_queue")
    first = next_waiting_upload(state)
    assert first is not None
    start_upload(state, first.identity)
    complete_upload(state, first.identity, status=UploadStatus.READY, document_id="one")

    incomplete = summarize_upload_queue(state, duration_ms=1.0, identities=identities)
    assert incomplete.finished is False

    second = next_waiting_upload(state)
    assert second is not None
    start_upload(state, second.identity)
    complete_upload(state, second.identity, status=UploadStatus.READY, document_id="two")
    end_operation(state, operation)
    finished = summarize_upload_queue(state, duration_ms=2.0, identities=identities)

    assert finished.finished is True
    assert finished.indexed_count == 2
    assert state[ACTIVE_UPLOAD_IDENTITY] is None
