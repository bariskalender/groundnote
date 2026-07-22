from __future__ import annotations

import inspect
import time

from groundnote.app import _chat_busy_message, _indexing_progress_label
from groundnote.performance import IndexingProgress, IndexingStage
from groundnote.ui.components.upload import render_upload_control
from groundnote.ui.state import OperationState
from groundnote.ui.text import t


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
    assert t("operation_busy_upload", "en") == (
        "GroundNote is indexing a document. Upload another file after it finishes."
    )
    assert t("operation_busy_upload", "en") != t("chat_busy_indexing", "en")


def test_uploader_contract_is_single_file_without_queue_controls() -> None:
    source = inspect.getsource(render_upload_control)

    assert "accept_multiple_files=False" in source
    assert "queue" not in source.casefold()
    assert "cancel" not in source.casefold()


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
