"""Explicit, lazy-model application composition for the Streamlit UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from groundnote.ai.foundry_chat import FoundryChatProvider
from groundnote.ai.foundry_embeddings import FoundryEmbeddingProvider
from groundnote.ai.foundry_manager import FoundryManager
from groundnote.ai.interfaces import ChatProvider
from groundnote.ai.lifecycle import ChatModelLifecycle
from groundnote.bootstrap import ApplicationDependencies, initialize_application
from groundnote.config import Settings
from groundnote.documents import DocumentProcessingService
from groundnote.embeddings import EmbeddingService
from groundnote.embeddings.models import BatchEmbeddingProvider
from groundnote.rag import RagService
from groundnote.retrieval.service import SemanticRetrievalService
from groundnote.services import (
    DocumentIndexingService,
    DocumentIndexIntegrityService,
    PreEmbeddingIngestionService,
)
from groundnote.storage import SQLiteConnectionFactory, SQLiteUnitOfWorkFactory
from groundnote.ui.foundry_status import FoundryStatusService
from groundnote.ui.workflows import DocumentWorkflow, QuestionWorkflow


@dataclass(frozen=True)
class ApplicationContext:
    """Long-lived stateless services; model loading remains operation-scoped."""

    dependencies: ApplicationDependencies
    settings: Settings
    connection_factory: SQLiteConnectionFactory
    unit_of_work_factory: SQLiteUnitOfWorkFactory
    foundry_manager: FoundryManager
    chat_model_lifecycle: ChatModelLifecycle
    embedding_provider: BatchEmbeddingProvider
    chat_provider: ChatProvider
    fast_chat_provider: ChatProvider
    embedding_service: EmbeddingService
    document_processing_service: DocumentProcessingService
    ingestion_service: PreEmbeddingIngestionService
    indexing_service: DocumentIndexingService
    index_integrity_service: DocumentIndexIntegrityService
    retrieval_service: SemanticRetrievalService
    rag_service: RagService
    fast_rag_service: RagService
    document_workflow: DocumentWorkflow
    question_workflow: QuestionWorkflow
    fast_question_workflow: QuestionWorkflow
    foundry_status_service: FoundryStatusService


def build_application_context(
    settings: Settings | None = None,
    *,
    embedding_provider: BatchEmbeddingProvider | None = None,
    chat_provider: ChatProvider | None = None,
    foundry_status_service: FoundryStatusService | None = None,
) -> ApplicationContext:
    """Build all services without downloading or loading a local model."""
    dependencies = initialize_application(settings)
    resolved_settings = dependencies.settings
    if resolved_settings.database_path is None:
        raise RuntimeError("Database path is not configured.")
    connection_factory = SQLiteConnectionFactory(resolved_settings.database_path)
    unit_of_work_factory = dependencies.unit_of_work_factory
    manager = FoundryManager(app_name="groundnote")
    resolved_embedding_provider = cast(
        BatchEmbeddingProvider,
        embedding_provider
        or FoundryEmbeddingProvider(
            resolved_settings.embedding_model,
            manager,
        ),
    )
    resolved_chat_provider = chat_provider or FoundryChatProvider(
        resolved_settings.chat_model,
        manager,
    )
    raw_fast_chat_provider = FoundryChatProvider(resolved_settings.fast_chat_model, manager)
    chat_model_lifecycle = ChatModelLifecycle()
    managed_chat_provider = chat_model_lifecycle.register(resolved_chat_provider)
    fast_chat_provider = chat_model_lifecycle.register(raw_fast_chat_provider)
    embedding_service = EmbeddingService(
        settings=resolved_settings,
        provider=resolved_embedding_provider,
    )
    document_processing_service = DocumentProcessingService(settings=resolved_settings)
    ingestion_service = PreEmbeddingIngestionService(
        settings=resolved_settings,
        unit_of_work_factory=unit_of_work_factory,
    )
    indexing_service = DocumentIndexingService(
        settings=resolved_settings,
        unit_of_work_factory=unit_of_work_factory,
        embedding_service=embedding_service,
    )
    index_integrity_service = DocumentIndexIntegrityService(
        settings=resolved_settings,
        unit_of_work_factory=unit_of_work_factory,
    )
    retrieval_service = SemanticRetrievalService(
        settings=resolved_settings,
        connection_factory=connection_factory,
        embedding_service=embedding_service,
    )
    rag_service = RagService(
        settings=resolved_settings,
        retrieval_service=retrieval_service,
        chat_provider=managed_chat_provider,
    )
    fast_settings = resolved_settings.model_copy(
        update={
            "rag_max_output_tokens": min(resolved_settings.rag_max_output_tokens, 256),
        }
    )
    fast_rag_service = RagService(
        settings=fast_settings,
        retrieval_service=retrieval_service,
        chat_provider=fast_chat_provider,
    )
    document_workflow = DocumentWorkflow(
        settings=resolved_settings,
        unit_of_work_factory=unit_of_work_factory,
        ingestion_service=ingestion_service,
        indexing_service=indexing_service,
        index_integrity_service=index_integrity_service,
    )
    question_workflow = QuestionWorkflow(
        document_workflow=document_workflow,
        rag_service=rag_service,
    )
    fast_question_workflow = QuestionWorkflow(
        document_workflow=document_workflow,
        rag_service=fast_rag_service,
    )
    return ApplicationContext(
        dependencies=dependencies,
        settings=resolved_settings,
        connection_factory=connection_factory,
        unit_of_work_factory=unit_of_work_factory,
        foundry_manager=manager,
        chat_model_lifecycle=chat_model_lifecycle,
        embedding_provider=resolved_embedding_provider,
        chat_provider=managed_chat_provider,
        fast_chat_provider=fast_chat_provider,
        embedding_service=embedding_service,
        document_processing_service=document_processing_service,
        ingestion_service=ingestion_service,
        indexing_service=indexing_service,
        index_integrity_service=index_integrity_service,
        retrieval_service=retrieval_service,
        rag_service=rag_service,
        fast_rag_service=fast_rag_service,
        document_workflow=document_workflow,
        question_workflow=question_workflow,
        fast_question_workflow=fast_question_workflow,
        foundry_status_service=foundry_status_service or FoundryStatusService(),
    )


def unload_local_models(context: ApplicationContext) -> list[str]:
    """Best-effort local model cleanup for the current Streamlit session."""
    warnings: list[str] = []
    try:
        context.embedding_service.unload()
    except Exception:
        warnings.append("embedding_unload_failed")
    warnings.extend(context.chat_model_lifecycle.shutdown())
    return warnings
