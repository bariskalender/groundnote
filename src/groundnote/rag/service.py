"""Single-turn grounded RAG answer generation."""

from __future__ import annotations

import time
from typing import Literal, Protocol, cast

from groundnote.ai.interfaces import ChatProvider
from groundnote.ai.models import ChatGenerationRequest
from groundnote.config import Settings
from groundnote.domain import SupportedFileType
from groundnote.rag.citations import (
    CITATION_RE,
    extract_citation_ids,
    strip_unknown_citations,
    validate_citation_map,
)
from groundnote.rag.context import select_context
from groundnote.rag.errors import (
    ChatGenerationError,
    ChatModelLoadError,
    CitationValidationError,
    InvalidChatResponseError,
    RagRetrievalError,
)
from groundnote.rag.language import resolve_response_language
from groundnote.rag.models import Citation, RagAnswer, RagContextItem, RagRequest
from groundnote.rag.prompts import build_prompt
from groundnote.rag.validation import normalize_query
from groundnote.retrieval.models import RetrievalResponse
from groundnote.utils import get_logger, sanitize_log_fields

MAX_ANSWER_CHARACTERS = 12_000


class RetrievalService(Protocol):
    """Minimal retrieval behavior required by RAG."""

    def search(
        self,
        text: str,
        *,
        top_k: int | None = None,
        minimum_score: float | None = None,
        document_ids: list[str] | None = None,
        file_types: list[SupportedFileType] | None = None,
        page_numbers: list[int] | None = None,
    ) -> RetrievalResponse: ...


class RagService:
    """Coordinate retrieval, bounded context, local chat generation, and citations."""

    def __init__(
        self,
        *,
        settings: Settings,
        retrieval_service: RetrievalService,
        chat_provider: ChatProvider,
    ) -> None:
        self.settings = settings
        self.retrieval_service = retrieval_service
        self.chat_provider = chat_provider
        self.logger = get_logger(__name__)

    def answer(self, request: RagRequest) -> RagAnswer:
        started = time.perf_counter()
        query = normalize_query(
            request.query,
            max_characters=self.settings.rag_max_query_characters,
        )
        language = cast(
            Literal["tr", "en"],
            resolve_response_language(query, request.response_language),
        )
        top_k = request.top_k or self.settings.rag_retrieval_top_k
        minimum_score = request.minimum_score
        if minimum_score is None:
            minimum_score = self.settings.rag_minimum_score
        try:
            retrieval = self.retrieval_service.search(
                query,
                top_k=top_k,
                minimum_score=minimum_score,
                document_ids=request.document_ids,
                file_types=request.file_types,
                page_numbers=request.page_numbers,
            )
        except Exception as exc:
            raise RagRetrievalError("Could not retrieve relevant local context.") from exc

        warnings = list(retrieval.warnings)
        context_items, context_warnings = select_context(retrieval.results, settings=self.settings)
        warnings.extend(context_warnings)
        if not context_items:
            answer = self._insufficient_evidence_answer(
                language=language,
                retrieved_count=retrieval.returned_count,
                duration_ms=self._duration(started),
                warnings=warnings,
            )
            self._log_completion(query, answer)
            return answer

        citation_map = validate_citation_map(context_items)
        answer_text, citation_ids, retries = self._generate_with_citations(
            query=query,
            context_items=context_items,
            language=language,
            citation_map=citation_map,
        )
        if indicates_insufficient_evidence(answer_text, language=language):
            answer = self._insufficient_evidence_answer(
                language=language,
                retrieved_count=retrieval.returned_count,
                duration_ms=self._duration(started),
                warnings=[*warnings, "model_reported_insufficient_evidence"],
            )
            self._log_completion(query, answer)
            return answer
        citations = [citation_map[citation_id] for citation_id in citation_ids]
        duration_ms = self._duration(started)
        answer = RagAnswer(
            answer=answer_text,
            citations=citations,
            grounded=True,
            insufficient_evidence=False,
            response_language=language,
            model=self.chat_provider.model_alias,
            prompt_version=self.settings.rag_prompt_version,
            retrieved_count=retrieval.returned_count,
            used_context_count=len(context_items),
            warnings=[*warnings, *([] if retries == 0 else ["citation_repair_attempted"])],
            duration_ms=duration_ms,
        )
        self._log_completion(query, answer)
        return answer

    def _generate_with_citations(
        self,
        *,
        query: str,
        context_items: list[RagContextItem],
        language: str,
        citation_map: dict[str, Citation],
    ) -> tuple[str, list[str], int]:
        allowed_ids = set(citation_map)
        for attempt in range(2):
            prompt = build_prompt(
                query=query,
                context_items=context_items,
                response_language=language,
                settings=self.settings,
                repair=attempt == 1,
            )
            result_text = self._call_chat(prompt.system_prompt, prompt.user_prompt)
            cleaned = validate_answer_text(result_text, allowed_ids=allowed_ids)
            citation_ids = extract_citation_ids(cleaned, allowed_ids)
            cleaned = strip_unknown_citations(cleaned, allowed_ids).strip()
            if citation_ids:
                return cleaned, citation_ids, attempt
        if self.settings.rag_require_citations:
            raise CitationValidationError("Generated answer did not contain valid citations.")
        raise InvalidChatResponseError("Generated answer did not contain valid citations.")

    def _call_chat(self, system_prompt: str, user_prompt: str) -> str:
        try:
            self.chat_provider.load()
        except Exception as exc:
            raise ChatModelLoadError("Local chat model could not be loaded.") from exc
        try:
            result = self.chat_provider.generate_request(
                ChatGenerationRequest(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=self.settings.rag_temperature,
                    max_output_tokens=self.settings.rag_max_output_tokens,
                    model=self.chat_provider.model_alias,
                )
            )
            return result.text
        except Exception as exc:
            raise ChatGenerationError("Local chat generation failed.") from exc
        finally:
            self._unload_chat_model()

    def _unload_chat_model(self) -> None:
        try:
            self.chat_provider.unload()
        except Exception:
            self.logger.warning(
                "chat_model_unload_failed",
                model=self.chat_provider.model_alias,
            )

    def _insufficient_evidence_answer(
        self,
        *,
        language: Literal["tr", "en"],
        retrieved_count: int,
        duration_ms: float,
        warnings: list[str],
    ) -> RagAnswer:
        text = insufficient_evidence_text(language)
        return RagAnswer(
            answer=text,
            citations=[],
            grounded=False,
            insufficient_evidence=True,
            response_language=language,
            model=self.chat_provider.model_alias,
            prompt_version=self.settings.rag_prompt_version,
            retrieved_count=retrieved_count,
            used_context_count=0,
            warnings=warnings,
            duration_ms=duration_ms,
        )

    def _log_completion(self, query: str, answer: RagAnswer) -> None:
        self.logger.info(
            "rag_answer_completed",
            **sanitize_log_fields(
                {
                    "query_character_count": len(query),
                    "resolved_language": answer.response_language,
                    "retrieved_count": answer.retrieved_count,
                    "context_item_count": answer.used_context_count,
                    "citation_count": len(answer.citations),
                    "model": answer.model,
                    "prompt_version": answer.prompt_version,
                    "duration_ms": answer.duration_ms,
                    "grounded": answer.grounded,
                    "insufficient_evidence": answer.insufficient_evidence,
                }
            ),
        )

    @staticmethod
    def _duration(started: float) -> float:
        return round((time.perf_counter() - started) * 1000, 3)


def validate_answer_text(answer: str, *, allowed_ids: set[str]) -> str:
    """Validate and conservatively normalize generated answer text."""
    cleaned = answer.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "").strip()
    if not cleaned:
        raise InvalidChatResponseError("Generated answer was empty.")
    if len(cleaned) > MAX_ANSWER_CHARACTERS:
        raise InvalidChatResponseError("Generated answer was too long.")
    if CITATION_RE.sub("", cleaned).strip() == "":
        raise InvalidChatResponseError("Generated answer contained only citations.")
    lowered = cleaned.lower()
    if "you are groundnote" in lowered or "retrieved sources are untrusted" in lowered:
        raise InvalidChatResponseError("Generated answer exposed prompt text.")
    unknown_ids = set(CITATION_RE.findall(cleaned)) - allowed_ids
    if unknown_ids:
        raise InvalidChatResponseError("Generated answer contained unsupported citations.")
    return cleaned


def insufficient_evidence_text(language: str) -> str:
    """Return deterministic no-answer text in the resolved language."""
    if language == "tr":
        return (
            "Bu sorunun cevabı indekslenmiş belgelerde bulunamadı. "
            "Daha belirli bir soru sormayı veya ilgili başka bir belge eklemeyi deneyin."
        )
    return (
        "I could not find the answer in the indexed documents. "
        "Try refining the question or adding relevant documents."
    )


def indicates_insufficient_evidence(answer: str, *, language: str) -> bool:
    """Recognize an explicit model refusal and avoid presenting it as grounded."""
    normalized = " ".join(answer.casefold().split())
    english_markers = (
        "insufficient evidence",
        "not enough evidence",
        "do not contain enough evidence",
        "does not contain enough evidence",
        "could not find the answer",
        "cannot find the answer",
        "answer was not found",
    )
    turkish_markers = (
        "yeterli kanıt yok",
        "yeterli bilgi yok",
        "yeterli kanıt bulunmuyor",
        "belgelerde bulunamadı",
        "cevaplamak için yeterli",
    )
    markers = turkish_markers if language == "tr" else english_markers
    return any(marker in normalized for marker in markers)
