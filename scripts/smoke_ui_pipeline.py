"""Deterministic fake-provider smoke for the Phase 7 UI service boundary."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from groundnote.ai.fakes import FakeChatProvider, FakeEmbeddingProvider
from groundnote.config import Settings
from groundnote.ui import build_application_context
from groundnote.ui.models import UploadOutcomeKind


def main() -> int:
    """Run upload, persistence, RAG, insufficient-evidence, and duplicate checks."""
    with tempfile.TemporaryDirectory(prefix="groundnote-ui-fake-") as temporary:
        settings = Settings(
            data_directory=Path(temporary) / "app",
            embedding_dimension=4,
            embedding_model="fake-embedding",
            embedding_version="fake-ui-v1",
            chat_model="fake-chat",
            rag_minimum_score=-1.0,
        )
        context = build_application_context(
            settings,
            embedding_provider=FakeEmbeddingProvider(dimension=4),
            chat_provider=FakeChatProvider(responses=["Vector search uses embeddings. [S1]"]),
        )
        document_bytes = b"# Vector Search\n\nVector search uses local embeddings."
        upload = context.document_workflow.process_and_index(
            original_filename="phase7-smoke.md",
            data=document_bytes,
        )
        grounded = context.question_workflow.answer(
            "What does vector search use?",
            document_ids=[upload.document.document_id],
        )
        insufficient = context.question_workflow.answer(
            "What is the orbital period of Neptune?",
            minimum_score=1.0,
        )
        duplicate = context.document_workflow.process_and_index(
            original_filename="same-content.md",
            data=document_bytes,
        )
        restarted = build_application_context(
            settings,
            embedding_provider=FakeEmbeddingProvider(dimension=4),
            chat_provider=FakeChatProvider(),
        )
        persisted = restarted.document_workflow.list_documents()
        passed = all(
            (
                upload.document.status.value == "indexed",
                grounded.answer.grounded,
                len(grounded.answer.citations) == 1,
                insufficient.answer.insufficient_evidence,
                insufficient.answer.citations == [],
                duplicate.kind is UploadOutcomeKind.DUPLICATE,
                len(persisted) == 1,
                persisted[0].status.value == "indexed",
                not hasattr(restarted.question_workflow, "history"),
            )
        )
        print(
            json.dumps(
                {
                    "passed": passed,
                    "document_status": upload.document.status.value,
                    "chunk_count": upload.document.chunk_count,
                    "indexed_chunk_count": upload.document.embedded_chunk_count,
                    "grounded": grounded.answer.grounded,
                    "citation_count": len(grounded.answer.citations),
                    "insufficient_evidence": insufficient.answer.insufficient_evidence,
                    "duplicate": duplicate.kind.value,
                    "persisted_after_restart": len(persisted),
                    "persistent_chat_history": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
