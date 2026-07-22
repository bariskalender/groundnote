from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from groundnote.ai.fakes import FakeChatProvider, FakeEmbeddingProvider
from groundnote.ai.models import EmbeddingBatchResult
from groundnote.config import Settings
from groundnote.ui import build_application_context, unload_local_models
from groundnote.ui.errors import map_exception
from groundnote.ui.state import initialize_session_state
from groundnote.ui.uploads import (
    UploadStatus,
    complete_upload,
    fail_upload,
    next_waiting_upload,
    register_selected_uploads,
    retained_upload_bytes,
    start_upload,
    summarize_upload_queue,
    upload_items,
)
from tests.integration.documents.conftest import write_docx


class FakeUpload:
    def __init__(self, name: str, data: bytes) -> None:
        self.name = name
        self.data = data
        self.size = len(data)

    def getvalue(self) -> bytes:
        return self.data


class SequentialEmbeddingProvider(FakeEmbeddingProvider):
    def __init__(self, *, fail_marker: str | None = None) -> None:
        super().__init__(dimension=4)
        self.fail_marker = fail_marker
        self.load_calls = 0
        self.unload_calls = 0
        self.batch_calls = 0
        self.active_calls = 0
        self.maximum_active_calls = 0

    def load(self) -> None:
        self.load_calls += 1
        super().load()

    def unload(self) -> None:
        self.unload_calls += 1
        super().unload()

    def embed_many(
        self,
        texts: Sequence[str],
        *,
        batch_size: int = 8,
    ) -> EmbeddingBatchResult:
        self.batch_calls += 1
        self.active_calls += 1
        self.maximum_active_calls = max(self.maximum_active_calls, self.active_calls)
        try:
            if self.fail_marker and any(self.fail_marker in text for text in texts):
                raise RuntimeError("synthetic private middle-item failure")
            return super().embed_many(texts, batch_size=batch_size)
        finally:
            self.active_calls -= 1


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        data_directory=tmp_path / "app",
        embedding_dimension=4,
        embedding_model="fake-embedding",
        embedding_version="fake-queue-v1",
        chat_model="fake-chat",
        keep_models_loaded=True,
    )


def _drain_queue(context, state: dict[str, object]) -> tuple[list[str], list[bool]]:
    order: list[str] = []
    model_reuse: list[bool] = []
    try:
        while (waiting := next_waiting_upload(state)) is not None:
            item = start_upload(state, waiting.identity)
            order.append(item.filename)
            before_ids = {
                document.document_id for document in context.document_workflow.list_documents()
            }
            try:
                assert item.data is not None
                outcome = context.document_workflow.process_and_index(
                    original_filename=item.filename,
                    data=item.data,
                    precomputed_sha256=item.content_sha256,
                )
            except Exception as exc:
                new_failed = [
                    document.document_id
                    for document in context.document_workflow.list_documents()
                    if document.document_id not in before_ids and document.status.value == "failed"
                ]
                fail_upload(
                    state,
                    item.identity,
                    message=map_exception(exc),
                    document_id=new_failed[0] if len(new_failed) == 1 else None,
                )
                continue
            terminal = (
                UploadStatus.DUPLICATE if outcome.kind.value == "duplicate" else UploadStatus.READY
            )
            complete_upload(
                state,
                item.identity,
                status=terminal,
                document_id=outcome.document.document_id,
                duration_ms=outcome.duration_ms,
            )
            if outcome.diagnostics is not None:
                model_reuse.append(outcome.diagnostics.model_reused)
    finally:
        unload_local_models(context)
    return order, model_reuse


def test_three_mixed_valid_files_run_in_selection_order_with_one_warm_model(
    tmp_path: Path,
) -> None:
    docx_path = write_docx(tmp_path / "lecture notes.docx")
    provider = SequentialEmbeddingProvider()
    context = build_application_context(
        _settings(tmp_path),
        embedding_provider=provider,
        chat_provider=FakeChatProvider(),
    )
    state: dict[str, object] = {}
    initialize_session_state(state)
    identities = list(
        register_selected_uploads(
            state,
            [
                FakeUpload("Türkçe notlar.md", b"# Ders\n\nYerel not bir."),
                FakeUpload("lecture notes.docx", docx_path.read_bytes()),
                FakeUpload("plain notes.txt", b"A separate plain text study note."),
            ],
        ).queued
    )

    order, reuse = _drain_queue(context, state)
    summary = summarize_upload_queue(state, duration_ms=1.0, identities=identities)

    assert order == ["Türkçe notlar.md", "lecture notes.docx", "plain notes.txt"]
    assert summary.finished and summary.indexed_count == 3
    assert reuse == [False, True, True]
    assert provider.load_calls == 1
    assert provider.maximum_active_calls == 1
    assert provider.loaded is False
    assert retained_upload_bytes(state) == 0


def test_valid_duplicate_invalid_queue_continues_with_accurate_terminal_counts(
    tmp_path: Path,
) -> None:
    provider = SequentialEmbeddingProvider()
    context = build_application_context(
        _settings(tmp_path),
        embedding_provider=provider,
        chat_provider=FakeChatProvider(),
    )
    existing = b"This content is already indexed."
    context.document_workflow.process_and_index(original_filename="existing.txt", data=existing)
    state: dict[str, object] = {}
    initialize_session_state(state)
    identities = list(
        register_selected_uploads(
            state,
            [
                FakeUpload("valid.txt", b"A new valid queue document."),
                FakeUpload("duplicate copy.txt", existing),
                FakeUpload("invalid.pdf", b"not a real PDF"),
                FakeUpload("duplicate second name.txt", existing),
            ],
        ).queued
    )

    order, _ = _drain_queue(context, state)
    summary = summarize_upload_queue(state, duration_ms=2.0, identities=identities)

    assert order == [
        "valid.txt",
        "duplicate copy.txt",
        "invalid.pdf",
        "duplicate second name.txt",
    ]
    assert summary.indexed_count == 1
    assert summary.duplicate_count == 2
    assert summary.failed_count == 1
    assert summary.finished
    assert provider.maximum_active_calls == 1
    assert provider.loaded is False


def test_middle_embedding_failure_unloads_then_allows_third_item_and_final_cleanup(
    tmp_path: Path,
) -> None:
    provider = SequentialEmbeddingProvider(fail_marker="FAIL_EMBEDDING")
    context = build_application_context(
        _settings(tmp_path),
        embedding_provider=provider,
        chat_provider=FakeChatProvider(),
    )
    state: dict[str, object] = {}
    initialize_session_state(state)
    identities = list(
        register_selected_uploads(
            state,
            [
                FakeUpload("first.txt", b"First valid study note."),
                FakeUpload("middle.txt", b"FAIL_EMBEDDING in this document."),
                FakeUpload("third.txt", b"Third valid study note after failure."),
            ],
        ).queued
    )

    order, _ = _drain_queue(context, state)
    summary = summarize_upload_queue(state, duration_ms=3.0, identities=identities)

    assert order == ["first.txt", "middle.txt", "third.txt"]
    assert [item.status for item in upload_items(state)] == [
        UploadStatus.READY,
        UploadStatus.FAILED,
        UploadStatus.READY,
    ]
    assert summary.indexed_count == 2
    assert summary.failed_count == 1
    assert summary.finished
    assert provider.load_calls == 2
    assert provider.maximum_active_calls == 1
    assert provider.loaded is False
    assert retained_upload_bytes(state) == 0


def test_final_embedding_failure_still_unloads_model_and_releases_all_buffers(
    tmp_path: Path,
) -> None:
    provider = SequentialEmbeddingProvider(fail_marker="FINAL_FAILURE")
    context = build_application_context(
        _settings(tmp_path),
        embedding_provider=provider,
        chat_provider=FakeChatProvider(),
    )
    state: dict[str, object] = {}
    initialize_session_state(state)
    identities = list(
        register_selected_uploads(
            state,
            [
                FakeUpload("first.txt", b"First valid queue item."),
                FakeUpload("last.txt", b"FINAL_FAILURE in the final item."),
            ],
        ).queued
    )

    order, _ = _drain_queue(context, state)
    summary = summarize_upload_queue(state, duration_ms=4.0, identities=identities)

    assert order == ["first.txt", "last.txt"]
    assert summary.indexed_count == 1
    assert summary.failed_count == 1
    assert summary.finished
    assert provider.maximum_active_calls == 1
    assert provider.loaded is False
    assert retained_upload_bytes(state) == 0
