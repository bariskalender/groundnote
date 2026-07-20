"""Explicit, lazy-model application composition for the Streamlit UI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from groundnote.ai.foundry_chat import FoundryChatProvider
from groundnote.ai.foundry_embeddings import FoundryEmbeddingProvider
from groundnote.ai.foundry_manager import FoundryManager
from groundnote.ai.interfaces import ChatProvider
from groundnote.bootstrap import ApplicationDependencies, initialize_application
from groundnote.config import Settings
from groundnote.documents import DocumentProcessingService
from groundnote.embeddings import EmbeddingService
from groundnote.embeddings.models import BatchEmbeddingProvider
from groundnote.rag import RagService
from groundnote.retrieval.service import SemanticRetrievalService
from groundnote.services import DocumentIndexingService, PreEmbeddingIngestionService
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
    embedding_provider: BatchEmbeddingProvider
    chat_provider: ChatProvider
    embedding_service: EmbeddingService
    document_processing_service: DocumentProcessingService
    ingestion_service: PreEmbeddingIngestionService
    indexing_service: DocumentIndexingService
    retrieval_service: SemanticRetrievalService
    rag_service: RagService
    document_workflow: DocumentWorkflow
    question_workflow: QuestionWorkflow
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
    retrieval_service = SemanticRetrievalService(
        settings=resolved_settings,
        connection_factory=connection_factory,
        embedding_service=embedding_service,
    )
    rag_service = RagService(
        settings=resolved_settings,
        retrieval_service=retrieval_service,
        chat_provider=resolved_chat_provider,
    )
    document_workflow = DocumentWorkflow(
        settings=resolved_settings,
        unit_of_work_factory=unit_of_work_factory,
        ingestion_service=ingestion_service,
        indexing_service=indexing_service,
    )
    question_workflow = QuestionWorkflow(
        document_workflow=document_workflow,
        rag_service=rag_service,
    )
    return ApplicationContext(
        dependencies=dependencies,
        settings=resolved_settings,
        connection_factory=connection_factory,
        unit_of_work_factory=unit_of_work_factory,
        foundry_manager=manager,
        embedding_provider=resolved_embedding_provider,
        chat_provider=resolved_chat_provider,
        embedding_service=embedding_service,
        document_processing_service=document_processing_service,
        ingestion_service=ingestion_service,
        indexing_service=indexing_service,
        retrieval_service=retrieval_service,
        rag_service=rag_service,
        document_workflow=document_workflow,
        question_workflow=question_workflow,
        foundry_status_service=foundry_status_service or FoundryStatusService(),
    )
