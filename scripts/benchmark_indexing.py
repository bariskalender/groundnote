"""Profile one isolated GroundNote indexing operation with sanitized output."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from groundnote.ai.fakes import FakeChatProvider, FakeEmbeddingProvider
from groundnote.config import Settings
from groundnote.ui import build_application_context, unload_local_models


def main() -> int:
    """Index an explicit file or generated fixture without touching the user database."""
    args = _parse_args()
    data, original_filename, fixture_kind = _input_data(args)
    with tempfile.TemporaryDirectory(prefix="groundnote-index-benchmark-") as temporary:
        settings = Settings(
            data_directory=Path(temporary) / "app",
            embedding_batch_size=args.batch_size,
            keep_models_loaded=False,
        )
        embedding_provider = None if args.real_foundry else FakeEmbeddingProvider(dimension=1024)
        context = build_application_context(
            settings,
            embedding_provider=embedding_provider,
            chat_provider=FakeChatProvider(),
        )
        loaded_before = _loaded_model_count(context)
        cleanup_warnings: list[str] = []
        try:
            outcome = context.document_workflow.process_and_index(
                original_filename=original_filename,
                data=data,
                precomputed_sha256=hashlib.sha256(data).hexdigest(),
            )
            diagnostics = outcome.diagnostics
            if diagnostics is None:
                raise RuntimeError("Indexing did not return diagnostics.")
            payload = {
                "provider": "foundry-local" if args.real_foundry else "deterministic-fake",
                "fixture": fixture_kind,
                "document_status": outcome.document.status.value,
                "loaded_model_count_before": loaded_before,
                "loaded_model_count_after_indexing": _loaded_model_count(context),
                "metrics": asdict(diagnostics),
            }
        finally:
            cleanup_warnings = unload_local_models(context)

        payload["loaded_model_count_after_cleanup"] = _loaded_model_count(context)
        payload["cleanup_warning_count"] = len(cleanup_warnings)
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if not cleanup_warnings else 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--file",
        type=Path,
        help="Explicit PDF, DOCX, TXT, or Markdown input; its path and content are never printed.",
    )
    parser.add_argument("--sections", type=int, default=120)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument(
        "--real-foundry",
        action="store_true",
        help="Use the configured local embedding model. No model is downloaded automatically.",
    )
    args = parser.parse_args()
    if args.sections < 1 or args.sections > 2_000:
        parser.error("--sections must be between 1 and 2000")
    if args.batch_size < 1 or args.batch_size > 64:
        parser.error("--batch-size must be between 1 and 64")
    return args


def _input_data(args: argparse.Namespace) -> tuple[bytes, str, str]:
    if args.file is not None:
        path = args.file.resolve(strict=True)
        if path.suffix.lower() not in {".pdf", ".docx", ".txt", ".md", ".markdown"}:
            raise ValueError("The explicit benchmark file type is not supported.")
        return path.read_bytes(), f"benchmark{path.suffix.lower()}", "explicit-file"

    sections = [
        (
            f"## Topic {number}\n\n"
            "GroundNote keeps study material on the local computer. "
            "Each section contains representative technical notes about reliable indexing, "
            "bounded batches, citations, and private offline retrieval. "
            "Long-form lecture content explains how a learner reviews definitions, compares "
            "examples, checks evidence, and connects each concept to a practical exercise. "
            "The notes intentionally repeat a consistent structure so parser, chunker, storage, "
            "and embedding stages can be compared without using a private document. "
            "A final review sentence records expected behavior, limitations, and safe cleanup "
            "after the indexing operation completes.\n"
        )
        for number in range(1, args.sections + 1)
    ]
    return (
        ("# Representative Study Notes\n\n" + "\n".join(sections)).encode(),
        "benchmark.md",
        "generated-markdown",
    )


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
