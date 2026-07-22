"""Small real Foundry Local smoke representing the Phase 7 UI backend flow."""

from __future__ import annotations

import atexit
import json
import tempfile
from functools import partial
from pathlib import Path

from groundnote.config import Settings
from groundnote.ui import build_application_context, unload_local_models


def main() -> int:
    """Run one safe temporary upload with English, Turkish, and no-evidence questions."""
    with tempfile.TemporaryDirectory(prefix="groundnote-ui-real-") as temporary:
        settings = Settings(
            data_directory=Path(temporary) / "app",
            rag_minimum_score=-1.0,
            rag_max_output_tokens=240,
        )
        context = build_application_context(settings)
        cleanup = partial(unload_local_models, context)
        atexit.register(cleanup)
        upload = context.document_workflow.process_and_index(
            original_filename="phase7-local-smoke.md",
            data=(
                b"# GroundNote Storage\n\nGroundNote keeps study documents and indexes on the "
                b"local computer. Citations identify the source document."
            ),
        )
        english = context.question_workflow.answer(
            "Where does GroundNote keep study documents?",
            document_ids=[upload.document.document_id],
        )
        turkish = context.question_workflow.answer(
            "GroundNote çalışma belgelerini nerede tutar?",
            document_ids=[upload.document.document_id],
        )
        insufficient = context.question_workflow.answer(
            "What is the chemical composition of Neptune?",
            minimum_score=1.0,
        )
        passed = all(
            (
                upload.document.status.value == "indexed",
                upload.document.embedded_chunk_count == upload.document.chunk_count,
                english.answer.grounded,
                english.answer.response_language == "en",
                len(english.answer.citations) >= 1,
                turkish.answer.grounded,
                turkish.answer.response_language == "tr",
                len(turkish.answer.citations) >= 1,
                insufficient.answer.insufficient_evidence,
                insufficient.answer.citations == [],
            )
        )
        cleanup_warnings = cleanup()
        atexit.unregister(cleanup)
        passed = passed and not cleanup_warnings
        print(
            json.dumps(
                {
                    "passed": passed,
                    "document_status": upload.document.status.value,
                    "indexed_chunk_count": upload.document.embedded_chunk_count,
                    "english_grounded": english.answer.grounded,
                    "english_citations": len(english.answer.citations),
                    "turkish_grounded": turkish.answer.grounded,
                    "turkish_citations": len(turkish.answer.citations),
                    "insufficient_evidence": insufficient.answer.insufficient_evidence,
                    "embedding_model": settings.embedding_model,
                    "chat_model": settings.chat_model,
                    "cleanup_warning_count": len(cleanup_warnings),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
