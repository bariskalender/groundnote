from __future__ import annotations

from pathlib import Path

import groundnote.ui.app_context as app_context_module
from groundnote.ai.fakes import FakeChatProvider, FakeEmbeddingProvider
from groundnote.ai.models import ChatGenerationRequest, ChatGenerationResult
from groundnote.config import Settings
from groundnote.ui import build_application_context


class CountingChatProvider(FakeChatProvider):
    def __init__(self, model_alias: str) -> None:
        super().__init__(model_alias=model_alias)
        self.load_calls = 0
        self.unload_calls = 0

    def load(self) -> None:
        self.load_calls += 1
        super().load()

    def unload(self) -> None:
        self.unload_calls += 1
        super().unload()

    def generate_request(self, request: ChatGenerationRequest) -> ChatGenerationResult:
        return super().generate_request(request)


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


def test_balanced_then_fast_keeps_at_most_one_groundnote_chat_model_loaded(
    tmp_path: Path,
    monkeypatch,
) -> None:
    balanced = CountingChatProvider("balanced-chat")
    fast = CountingChatProvider("fast-chat")
    monkeypatch.setattr(
        app_context_module,
        "FoundryChatProvider",
        lambda _alias, _manager: fast,
    )
    settings = Settings(
        data_directory=tmp_path / "app",
        embedding_dimension=4,
        embedding_model="fake-embedding",
        chat_model="balanced-chat",
        fast_chat_model="fast-chat",
        keep_models_loaded=True,
    )
    context = build_application_context(
        settings,
        embedding_provider=FakeEmbeddingProvider(dimension=4),
        chat_provider=balanced,
    )

    context.rag_service._call_chat("system", "user")
    context.fast_rag_service._call_chat("system", "user")

    assert sum((balanced.loaded, fast.loaded)) <= 1
    assert balanced.unload_calls == 1
