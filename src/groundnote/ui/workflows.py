"""Testable UI orchestration over existing GroundNote service boundaries."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Literal, cast

from groundnote.config import Settings
from groundnote.documents import DuplicateDocumentError
from groundnote.documents.uploads import write_uploaded_bytes
from groundnote.domain import Document, DocumentStatus, SupportedFileType
from groundnote.rag import (
    QueryIntent,
    RagAnswer,
    RagRequest,
    RagService,
    deterministic_response,
    route_query,
)
from groundnote.services import DocumentIndexingService, PreEmbeddingIngestionService
from groundnote.storage import SQLiteUnitOfWorkFactory
from groundnote.ui.errors import InvalidFilterError, NoFileSelectedError
from groundnote.ui.models import (
    DocumentSummary,
    QuestionOutcome,
    UploadOutcome,
    UploadOutcomeKind,
    UploadStage,
)

StageCallback = Callable[[UploadStage], None]
PROCESSING_DOCUMENT_STATUSES = {
    DocumentStatus.PENDING,
    DocumentStatus.PENDING_EMBEDDING,
    DocumentStatus.INDEXING,
}


class DocumentWorkflow:
    """Coordinate upload, ingestion, indexing, and safe document reads."""

    def __init__(
        self,
        *,
        settings: Settings,
        unit_of_work_factory: SQLiteUnitOfWorkFactory,
        ingestion_service: PreEmbeddingIngestionService,
        indexing_service: DocumentIndexingService,
    ) -> None:
        self.settings = settings
        self.unit_of_work_factory = unit_of_work_factory
        self.ingestion_service = ingestion_service
        self.indexing_service = indexing_service

    def process_and_index(
        self,
        *,
        original_filename: str,
        data: bytes,
        on_stage: StageCallback | None = None,
    ) -> UploadOutcome:
        """Process one confirmed upload synchronously through existing services."""
        if not original_filename:
            raise NoFileSelectedError("No upload was selected.")
        if self.settings.document_directory is None:
            raise RuntimeError("Document directory is not configured.")
        started = time.perf_counter()
        self._notify(on_stage, UploadStage.SAVING)
        stored_path = write_uploaded_bytes(
            data,
            original_filename=original_filename,
            target_directory=self.settings.document_directory,
        )
        ingestion_completed = False
        try:
            self._notify(on_stage, UploadStage.PROCESSING)
            plan = self.ingestion_service.ingest_file(
                stored_path,
                original_filename=original_filename,
                allowed_directory=self.settings.document_directory,
            )
            ingestion_completed = True
        except DuplicateDocumentError as exc:
            _remove_file(stored_path)
            existing = self._existing_duplicate(exc)
            return UploadOutcome(
                kind=UploadOutcomeKind.DUPLICATE,
                document=existing,
                section_count=None,
                warnings=[],
                duration_ms=_elapsed_ms(started),
            )
        except Exception:
            _remove_file(stored_path)
            raise

        document_id = _document_id_from_plan(plan)
        if plan.document_status != DocumentStatus.PENDING_EMBEDDING:
            raise RuntimeError("Document ingestion did not reach the indexing boundary.")
        try:
            self._notify(on_stage, UploadStage.INDEXING)
            indexing = self.indexing_service.index_document(document_id)
            self._notify(on_stage, UploadStage.FINALIZING)
            if indexing.status != DocumentStatus.INDEXED:
                raise RuntimeError("Document indexing did not complete.")
            document = self.get_document(document_id)
            self._notify(on_stage, UploadStage.READY)
            return UploadOutcome(
                kind=UploadOutcomeKind.SUCCESS,
                document=document,
                section_count=len(plan.parsed_document.sections),
                warnings=[*plan.warnings, *indexing.warnings],
                duration_ms=_elapsed_ms(started),
            )
        except Exception:
            if not ingestion_completed:
                _remove_file(stored_path)
            raise

    def list_documents(self) -> list[DocumentSummary]:
        """Read current safe document status without mutating or loading models."""
        with self.unit_of_work_factory() as unit_of_work:
            if unit_of_work.documents is None or unit_of_work.vectors is None:
                raise RuntimeError("Document repositories are unavailable.")
            documents = unit_of_work.documents.list_all()
            summaries = [
                _summary(
                    document,
                    chunk_count=unit_of_work.vectors.count_chunks_for_document(document.id),
                    embedded_count=unit_of_work.vectors.count_embedded_chunks_for_document(
                        document.id
                    ),
                )
                for document in documents
            ]
        return list(reversed(summaries))

    def get_document(self, document_id: str) -> DocumentSummary:
        """Read one document using a short transaction."""
        with self.unit_of_work_factory() as unit_of_work:
            if unit_of_work.documents is None or unit_of_work.vectors is None:
                raise RuntimeError("Document repositories are unavailable.")
            document = unit_of_work.documents.get_by_id(document_id)
            return _summary(
                document,
                chunk_count=unit_of_work.vectors.count_chunks_for_document(document.id),
                embedded_count=unit_of_work.vectors.count_embedded_chunks_for_document(document.id),
            )

    def indexed_documents(self) -> list[DocumentSummary]:
        """Return only fully searchable documents for Ask filters."""
        return [
            document
            for document in self.list_documents()
            if document.status == DocumentStatus.INDEXED
        ]

    def _existing_duplicate(self, error: DuplicateDocumentError) -> DocumentSummary:
        if error.existing_document_id is None:
            raise RuntimeError("Duplicate document metadata is unavailable.") from error
        return self.get_document(error.existing_document_id)

    @staticmethod
    def _notify(callback: StageCallback | None, stage: UploadStage) -> None:
        if callback is not None:
            callback(stage)


class QuestionWorkflow:
    """Coordinate one independent RAG request through the existing RAG service."""

    def __init__(self, *, document_workflow: DocumentWorkflow, rag_service: RagService) -> None:
        self.document_workflow = document_workflow
        self.rag_service = rag_service

    def answer(
        self,
        question: str,
        *,
        document_ids: list[str] | None = None,
        file_types: list[SupportedFileType] | None = None,
        minimum_score: float | None = None,
        response_language: str | None = None,
    ) -> QuestionOutcome:
        """Answer once, forwarding validated source filters without persistent history."""
        started = time.perf_counter()
        routed = route_query(question, response_language=response_language)
        if routed.intent is not QueryIntent.DOCUMENT_QUESTION:
            answer = _deterministic_answer(
                deterministic_response(routed.intent, language=routed.language),
                language=routed.language,
                started=started,
                warning=f"intent_{routed.intent.value}",
            )
            return QuestionOutcome(
                question=question.strip(),
                answer=answer,
                document_ids=(),
                file_types=(),
            )
        documents = self.document_workflow.list_documents()
        indexed = [document for document in documents if document.status == DocumentStatus.INDEXED]
        if not indexed:
            language = routed.language
            processing = any(
                document.status in PROCESSING_DOCUMENT_STATUSES for document in documents
            )
            text = _no_ready_document_text(language, processing=processing)
            return QuestionOutcome(
                question=question.strip(),
                answer=_deterministic_answer(
                    text,
                    language=language,
                    started=started,
                    warning="no_ready_documents",
                    insufficient=True,
                ),
                document_ids=(),
                file_types=(),
            )
        request = build_rag_request(
            question,
            indexed_documents=indexed,
            document_ids=document_ids,
            file_types=file_types,
            minimum_score=minimum_score,
            response_language=response_language,
        )
        answer = self.rag_service.answer(request)
        return QuestionOutcome(
            question=question.strip(),
            answer=answer,
            document_ids=tuple(request.document_ids or ()),
            file_types=tuple(request.file_types or ()),
        )


def build_rag_request(
    question: str,
    *,
    indexed_documents: list[DocumentSummary],
    document_ids: list[str] | None,
    file_types: list[SupportedFileType] | None,
    minimum_score: float | None = None,
    response_language: str | None = None,
) -> RagRequest:
    """Build a filter-safe request; empty selections mean all indexed documents."""
    allowed_ids = {document.document_id for document in indexed_documents}
    selected_ids = list(dict.fromkeys(document_ids or []))
    if any(document_id not in allowed_ids for document_id in selected_ids):
        raise InvalidFilterError("A selected document is not indexed.")
    allowed_types = set(SupportedFileType)
    selected_types = list(dict.fromkeys(file_types or []))
    if any(file_type not in allowed_types for file_type in selected_types):
        raise InvalidFilterError("A selected file type is invalid.")
    resolved_language = cast(
        Literal["tr", "en", "auto"],
        response_language if response_language in {"tr", "en"} else "auto",
    )
    return RagRequest(
        query=question,
        document_ids=selected_ids or None,
        file_types=selected_types or None,
        minimum_score=minimum_score,
        response_language=resolved_language,
    )


def _document_id_from_plan(plan: object) -> str:
    chunks = getattr(plan, "chunks", None)
    if not chunks:
        raise RuntimeError("Document ingestion produced no chunks.")
    document_id = getattr(chunks[0], "document_id", None)
    if not isinstance(document_id, str) or not document_id:
        raise RuntimeError("Document ingestion result has no document id.")
    return document_id


def _summary(document: Document, *, chunk_count: int, embedded_count: int) -> DocumentSummary:
    return DocumentSummary(
        document_id=document.id,
        original_filename=document.original_filename,
        file_type=document.file_type,
        status=document.status,
        file_size_bytes=document.file_size_bytes,
        page_count=document.page_count,
        chunk_count=chunk_count,
        embedded_chunk_count=embedded_count,
        created_at=document.created_at,
        indexed_at=document.indexed_at,
        embedding_model=document.embedding_model,
        error_message=document.error_message,
    )


def _remove_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 3)


def _deterministic_answer(
    text: str,
    *,
    language: str,
    started: float,
    warning: str,
    insufficient: bool = False,
) -> RagAnswer:
    return RagAnswer(
        answer=text,
        citations=[],
        grounded=False,
        insufficient_evidence=insufficient,
        response_language=cast(Literal["tr", "en"], language),
        model="deterministic-router",
        prompt_version="intent-router-v2",
        retrieved_count=0,
        used_context_count=0,
        warnings=[warning],
        duration_ms=_elapsed_ms(started),
    )


def _no_ready_document_text(language: str, *, processing: bool) -> str:
    if language == "tr":
        if processing:
            return "Belgeler hazırlanıyor. İlk belge hazır olduğunda soru sorabilirsiniz."
        return "Önce bir belge yükleyin; sonra onun hakkında soru sorabilirsiniz."
    if processing:
        return "Documents are being prepared. You can ask once at least one document is ready."
    return "Please upload a document first, then ask a question about it."
