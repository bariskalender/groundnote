from __future__ import annotations

import time

from groundnote.app import _chat_busy_message, _indexing_progress_label, _queue_summary_message
from groundnote.performance import IndexingProgress, IndexingStage
from groundnote.ui.state import OperationState
from groundnote.ui.text import t
from groundnote.ui.uploads import UploadQueueSummary


def test_indexing_uses_chat_specific_busy_message_in_both_languages() -> None:
    operation = OperationState(
        operation_id="operation-id",
        operation_type="upload",
        started_at=time.time(),
    )

    assert _chat_busy_message(operation, "en") == (
        "GroundNote is indexing a document. Chat will be available when indexing finishes."
    )
    assert _chat_busy_message(operation, "tr") == (
        "GroundNote bir belgeyi indeksliyor. İndeksleme tamamlandığında sohbet yeniden "
        "kullanılabilir."
    )


def test_upload_busy_message_remains_separate_from_chat_message() -> None:
    assert "uploading another file" in t("operation_busy_upload", "en")
    assert t("operation_busy_upload", "en") != t("chat_busy_indexing", "en")


def test_upload_queue_blocks_chat_with_exact_plural_message() -> None:
    operation = OperationState(
        operation_id="queue-operation-id",
        operation_type="upload_queue",
        started_at=time.time(),
    )

    assert _chat_busy_message(operation, "en") == (
        "GroundNote is indexing documents. Chat will be available when the queue finishes."
    )
    assert _chat_busy_message(operation, "tr") == (
        "GroundNote belgeleri indeksliyor. Kuyruk tamamlandığında sohbet yeniden kullanılabilir."
    )


def test_upload_queue_summary_is_localized_from_terminal_counts() -> None:
    summary = UploadQueueSummary(
        total_count=5,
        indexed_count=2,
        duplicate_count=1,
        failed_count=1,
        interrupted_count=0,
        cancelled_count=1,
        duration_ms=2_000.0,
    )

    assert _queue_summary_message(summary, "en") == (
        "2 indexed, 1 already indexed, 1 failed, 1 cancelled. The upload queue finished in 2.00 s."
    )
    assert _queue_summary_message(summary, "tr") == (
        "2 belge indekslendi, 1 belge zaten indekslenmişti, 1 belge başarısız oldu, "
        "1 belge iptal edildi. Yükleme kuyruğu 2.00 s sürede tamamlandı."
    )


def test_embedding_progress_uses_real_units_and_elapsed_time_without_fake_percentage() -> None:
    progress = IndexingProgress(
        stage=IndexingStage.EMBEDDING,
        elapsed_ms=1234.0,
        completed_units=24,
        total_units=80,
        unit="chunks",
    )

    label = _indexing_progress_label(progress, "en")

    assert "Embedding chunks: 24 / 80" in label
    assert "1.23 s" in label
    assert "%" not in label
