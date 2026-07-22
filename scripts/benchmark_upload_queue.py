"""Measure an isolated three-file sequential upload queue with sanitized output."""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path
from typing import Any

from groundnote.ai.fakes import FakeChatProvider, FakeEmbeddingProvider
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
)


class GeneratedUpload:
    """Small in-memory fixture matching Streamlit's safe uploader contract."""

    def __init__(self, name: str, data: bytes) -> None:
        self.name = name
        self.data = data
        self.size = len(data)

    def getvalue(self) -> bytes:
        return self.data


def main() -> int:
    """Index three generated files without touching GroundNote's normal data directory."""
    args = _parse_args()
    uploads = _generated_uploads(args.sections)
    with tempfile.TemporaryDirectory(prefix="groundnote-upload-queue-") as temporary:
        settings = Settings(
            data_directory=Path(temporary) / "app",
            embedding_batch_size=args.batch_size,
            keep_models_loaded=True,
        )
        context = build_application_context(
            settings,
            embedding_provider=(
                None if args.real_foundry else FakeEmbeddingProvider(dimension=1024)
            ),
            chat_provider=FakeChatProvider(),
        )
        state: dict[str, object] = {}
        initialize_session_state(state)
        loaded_before = _loaded_model_count(context)
        registration = register_selected_uploads(
            state,
            uploads,
            maximum_file_count=settings.maximum_upload_files,
            maximum_total_bytes=settings.maximum_upload_total_size_mb * 1024 * 1024,
        )
        peak_retained_bytes = retained_upload_bytes(state)
        per_file: list[dict[str, Any]] = []
        peak_rss_mb: float | None = None
        started = time.perf_counter()
        active_count = 0
        maximum_active_count = 0
        cleanup_warnings: list[str] = []
        try:
            while (waiting := next_waiting_upload(state)) is not None:
                item = start_upload(state, waiting.identity)
                active_count += 1
                maximum_active_count = max(maximum_active_count, active_count)
                try:
                    if item.data is None:
                        raise RuntimeError("The generated queue item lost its byte buffer.")
                    outcome = context.document_workflow.process_and_index(
                        original_filename=item.filename,
                        data=item.data,
                        precomputed_sha256=item.content_sha256,
                    )
                    status = (
                        UploadStatus.DUPLICATE
                        if outcome.kind.value == "duplicate"
                        else UploadStatus.READY
                    )
                    complete_upload(
                        state,
                        item.identity,
                        status=status,
                        document_id=outcome.document.document_id,
                        duration_ms=outcome.duration_ms,
                    )
                    diagnostics = outcome.diagnostics
                    if diagnostics is not None and diagnostics.peak_process_rss_mb is not None:
                        peak_rss_mb = max(
                            peak_rss_mb or 0.0,
                            diagnostics.peak_process_rss_mb,
                        )
                    per_file.append(
                        {
                            "filename": item.filename,
                            "bytes": item.size_bytes,
                            "chunks": outcome.document.chunk_count,
                            "duration_ms": round(outcome.duration_ms, 2),
                            "model_reused": (
                                diagnostics.model_reused if diagnostics is not None else None
                            ),
                            "status": status.value,
                        }
                    )
                except Exception as exc:
                    fail_upload(state, item.identity, message=map_exception(exc))
                    per_file.append(
                        {
                            "filename": item.filename,
                            "bytes": item.size_bytes,
                            "status": UploadStatus.FAILED.value,
                            "error_category": type(exc).__name__,
                        }
                    )
                finally:
                    active_count -= 1
                    peak_retained_bytes = max(
                        peak_retained_bytes,
                        retained_upload_bytes(state),
                    )
            duration_ms = (time.perf_counter() - started) * 1000
            summary = summarize_upload_queue(
                state,
                duration_ms=duration_ms,
                peak_process_rss_mb=peak_rss_mb,
                identities=list(registration.queued),
            )
            loaded_after_queue = _loaded_model_count(context)
        finally:
            cleanup_warnings = unload_local_models(context)

        payload = {
            "provider": "foundry-local" if args.real_foundry else "deterministic-fake",
            "selected_file_count": len(uploads),
            "selected_bytes": sum(upload.size for upload in uploads),
            "peak_retained_upload_bytes": peak_retained_bytes,
            "final_retained_upload_bytes": retained_upload_bytes(state),
            "maximum_simultaneous_indexing_items": maximum_active_count,
            "queue_duration_ms": round(summary.duration_ms, 2),
            "peak_process_rss_mb": summary.peak_process_rss_mb,
            "indexed_count": summary.indexed_count,
            "duplicate_count": summary.duplicate_count,
            "failed_count": summary.failed_count,
            "finished": summary.finished,
            "loaded_model_count_before": loaded_before,
            "loaded_model_count_after_queue": loaded_after_queue,
            "loaded_model_count_after_cleanup": _loaded_model_count(context),
            "cleanup_warning_count": len(cleanup_warnings),
            "files": per_file,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        passed = all(
            (
                summary.finished,
                summary.indexed_count == 3,
                summary.failed_count == 0,
                maximum_active_count == 1,
                retained_upload_bytes(state) == 0,
                not cleanup_warnings,
                _loaded_model_count(context) in {0, None},
            )
        )
        return 0 if passed else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sections", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument(
        "--real-foundry",
        action="store_true",
        help="Use the cached local embedding model; no model is downloaded automatically.",
    )
    args = parser.parse_args()
    if args.sections < 1 or args.sections > 100:
        parser.error("--sections must be between 1 and 100")
    if args.batch_size < 1 or args.batch_size > 64:
        parser.error("--batch-size must be between 1 and 64")
    return args


def _generated_uploads(sections: int) -> list[GeneratedUpload]:
    documents = []
    for document_number in range(1, 4):
        section_text = "\n\n".join(
            (
                f"## Topic {section}\n\n"
                f"Generated study document {document_number} records bounded local indexing, "
                "source citations, privacy, and reliable queue cleanup. Each section has "
                "distinct representative wording for deterministic offline validation."
            )
            for section in range(1, sections + 1)
        )
        suffix = ".md" if document_number == 2 else ".txt"
        data = f"# Queue Fixture {document_number}\n\n{section_text}".encode()
        documents.append(GeneratedUpload(f"queue-fixture-{document_number}{suffix}", data))
    return documents


def _loaded_model_count(context: object) -> int | None:
    manager = getattr(context, "foundry_manager", None)
    if manager is None:
        return None
    try:
        return sum(model.is_loaded for model in manager.list_models())
    except Exception:
        return None


if __name__ == "__main__":
    raise SystemExit(main())
