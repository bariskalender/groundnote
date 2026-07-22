"""Operation-local indexing timings without document content or filesystem paths."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum

import psutil


class IndexingStage(StrEnum):
    """Truthful indexing stages shared by services and the UI."""

    SAVING_UPLOAD = "saving_upload"
    VALIDATING = "validating"
    HASHING = "hashing"
    DUPLICATE_CHECK = "duplicate_check"
    PARSING = "parsing"
    CHUNKING = "chunking"
    SAVING_CHUNKS = "saving_chunks"
    LOADING_EMBEDDING_MODEL = "loading_embedding_model"
    EMBEDDING = "embedding"
    SAVING_VECTORS = "saving_vectors"
    FTS_INDEXING = "fts_indexing"
    INTEGRITY_VERIFICATION = "integrity_verification"
    FINALIZATION = "finalization"


@dataclass(frozen=True)
class IndexingProgress:
    """One safe progress event with optional real unit counters."""

    stage: IndexingStage
    elapsed_ms: float
    completed_units: int | None = None
    total_units: int | None = None
    unit: str | None = None


@dataclass(frozen=True)
class IndexingDiagnostics:
    """Safe completed or failed operation metrics."""

    stage_durations_ms: dict[str, float]
    total_duration_ms: float
    file_size_bytes: int
    extracted_character_count: int
    page_count: int | None
    chunk_count: int
    embedding_batch_count: int
    embedding_batch_size: int
    model_load_duration_ms: float
    model_reused: bool
    peak_process_rss_mb: float | None
    process_cpu_percent: float | None
    hash_reused: bool
    failed_stage: str | None


ProgressCallback = Callable[[IndexingProgress], None]


class IndexingMetricsCollector:
    """Collect bounded operation metrics and sample process resources at stage boundaries."""

    def __init__(
        self,
        *,
        embedding_batch_size: int,
        on_progress: ProgressCallback | None = None,
    ) -> None:
        self.embedding_batch_size = embedding_batch_size
        self.on_progress = on_progress
        self._started = time.perf_counter()
        self._durations: dict[str, float] = {}
        self.file_size_bytes = 0
        self.extracted_character_count = 0
        self.page_count: int | None = None
        self.chunk_count = 0
        self.embedding_batch_count = 0
        self.model_reused = False
        self.hash_reused = False
        self.failed_stage: IndexingStage | None = None
        self._process = psutil.Process()
        self._process.cpu_percent(interval=None)
        self._peak_rss_mb = self._rss_mb()
        self._finished_cpu_percent: float | None = None

    @contextmanager
    def measure(self, stage: IndexingStage) -> Iterator[None]:
        """Measure one stage, preserving the first failed-stage identifier."""
        started = time.perf_counter()
        self.progress(stage)
        try:
            yield
        except BaseException:
            if self.failed_stage is None:
                self.failed_stage = stage
            raise
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            self._durations[stage.value] = round(
                self._durations.get(stage.value, 0.0) + duration_ms,
                3,
            )
            self._sample_resources()

    def record_zero(self, stage: IndexingStage) -> None:
        self._durations.setdefault(stage.value, 0.0)
        self.progress(stage)

    def progress(
        self,
        stage: IndexingStage,
        *,
        completed_units: int | None = None,
        total_units: int | None = None,
        unit: str | None = None,
    ) -> None:
        self._sample_resources()
        if self.on_progress is not None:
            self.on_progress(
                IndexingProgress(
                    stage=stage,
                    elapsed_ms=self.elapsed_ms,
                    completed_units=completed_units,
                    total_units=total_units,
                    unit=unit,
                )
            )

    @property
    def elapsed_ms(self) -> float:
        return round((time.perf_counter() - self._started) * 1000, 3)

    def snapshot(self) -> IndexingDiagnostics:
        self._sample_resources()
        if self._finished_cpu_percent is None:
            try:
                self._finished_cpu_percent = float(self._process.cpu_percent(interval=None))
            except (psutil.Error, OSError):
                self._finished_cpu_percent = None
        return IndexingDiagnostics(
            stage_durations_ms=dict(self._durations),
            total_duration_ms=self.elapsed_ms,
            file_size_bytes=self.file_size_bytes,
            extracted_character_count=self.extracted_character_count,
            page_count=self.page_count,
            chunk_count=self.chunk_count,
            embedding_batch_count=self.embedding_batch_count,
            embedding_batch_size=self.embedding_batch_size,
            model_load_duration_ms=self._durations.get(
                IndexingStage.LOADING_EMBEDDING_MODEL.value,
                0.0,
            ),
            model_reused=self.model_reused,
            peak_process_rss_mb=self._peak_rss_mb,
            process_cpu_percent=self._finished_cpu_percent,
            hash_reused=self.hash_reused,
            failed_stage=self.failed_stage.value if self.failed_stage is not None else None,
        )

    def _sample_resources(self) -> None:
        current = self._rss_mb()
        if current is not None and (self._peak_rss_mb is None or current > self._peak_rss_mb):
            self._peak_rss_mb = current

    def _rss_mb(self) -> float | None:
        try:
            return float(round(self._process.memory_info().rss / (1024 * 1024), 3))
        except (psutil.Error, OSError):
            return None
