from __future__ import annotations

import pytest

from groundnote.performance import IndexingMetricsCollector, IndexingStage


def test_metrics_are_numeric_bounded_metadata_without_private_text() -> None:
    secret = "PRIVATE_DOCUMENT_SENTENCE"
    collector = IndexingMetricsCollector(embedding_batch_size=8)
    collector.file_size_bytes = 2048
    collector.extracted_character_count = 1500
    collector.chunk_count = 3
    with collector.measure(IndexingStage.PARSING):
        pass

    diagnostics = collector.snapshot()

    assert diagnostics.total_duration_ms >= 0
    assert diagnostics.stage_durations_ms["parsing"] >= 0
    assert diagnostics.embedding_batch_size == 8
    assert diagnostics.peak_process_rss_mb is None or diagnostics.peak_process_rss_mb > 0
    assert secret not in repr(diagnostics)
    assert not hasattr(diagnostics, "filename")
    assert not hasattr(diagnostics, "path")


def test_first_failed_stage_is_retained_for_safe_retry_feedback() -> None:
    collector = IndexingMetricsCollector(embedding_batch_size=4)

    with (
        pytest.raises(RuntimeError, match="synthetic failure"),
        collector.measure(IndexingStage.EMBEDDING),
    ):
        raise RuntimeError("synthetic failure")

    diagnostics = collector.snapshot()
    assert diagnostics.failed_stage == "embedding"
    assert diagnostics.stage_durations_ms["embedding"] >= 0
