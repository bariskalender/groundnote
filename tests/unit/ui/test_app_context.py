from __future__ import annotations

from pathlib import Path

from groundnote.ai.fakes import FakeChatProvider, FakeEmbeddingProvider
from groundnote.config import Settings
from groundnote.ui import build_application_context


def test_application_context_construction_loads_no_model(tmp_path: Path) -> None:
    settings = Settings(
        data_directory=tmp_path / "app",
        embedding_dimension=4,
        embedding_model="fake-embedding",
        chat_model="fake-chat",
    )
    embedding = FakeEmbeddingProvider(dimension=4)
    chat = FakeChatProvider()

    context = build_application_context(
        settings,
        embedding_provider=embedding,
        chat_provider=chat,
    )

    assert context.settings is settings
    assert context.document_workflow is not None
    assert context.question_workflow is not None
    assert context.ingestion_service is not None
    assert context.indexing_service is not None
    assert context.retrieval_service is not None
    assert context.rag_service is not None
    assert embedding.loaded is False
    assert chat.loaded is False


def test_repeated_context_construction_is_safe_and_migrations_are_idempotent(
    tmp_path: Path,
) -> None:
    settings = Settings(
        data_directory=tmp_path / "app",
        embedding_dimension=4,
        embedding_model="fake-embedding",
        chat_model="fake-chat",
    )

    first = build_application_context(
        settings,
        embedding_provider=FakeEmbeddingProvider(dimension=4),
        chat_provider=FakeChatProvider(),
    )
    second = build_application_context(
        settings,
        embedding_provider=FakeEmbeddingProvider(dimension=4),
        chat_provider=FakeChatProvider(),
    )

    assert first.settings.database_path == second.settings.database_path
    assert first.document_workflow.list_documents() == []
    assert second.document_workflow.list_documents() == []
