from __future__ import annotations

import pytest

from groundnote.ai.fakes import FakeChatProvider
from groundnote.config import Settings
from groundnote.domain import SupportedFileType
from groundnote.rag import RagRequest, RagService
from groundnote.rag.router import QueryIntent, deterministic_response, route_query
from groundnote.retrieval.models import RetrievalResponse, RetrievalResult, SemanticQuery


class CountingRetrievalService:
    def __init__(self, results: list[RetrievalResult]) -> None:
        self.results = results
        self.calls = 0

    def search(self, text: str, **kwargs: object) -> RetrievalResponse:
        self.calls += 1
        return RetrievalResponse(
            query=SemanticQuery(text=text, top_k=5, minimum_score=0.0),
            results=self.results,
            candidate_count=len(self.results),
            returned_count=len(self.results),
            embedding_model="fake",
            duration_ms=1.0,
        )


def test_router_classifies_simple_turkish_greeting_without_rag() -> None:
    routed = route_query("merhaba nasılsın", response_language="tr")

    assert routed.intent is QueryIntent.GREETING
    assert routed.language == "tr"


@pytest.mark.parametrize("text", ["A", "?", "asd", "asdf", "aaaa", "."])
def test_router_rejects_short_unclear_inputs(text: str) -> None:
    routed = route_query(text, response_language="tr")

    assert routed.intent is QueryIntent.UNCLEAR
    assert "daha açık" in deterministic_response(routed.intent, language=routed.language)


@pytest.mark.parametrize("text", ["W123", "NVH", "CRC nedir?", "OM617", "VIN"])
def test_router_allows_short_domain_terms(text: str) -> None:
    routed = route_query(text, response_language="tr")

    assert routed.intent is QueryIntent.DOCUMENT_QUESTION


def test_router_handles_empty_input() -> None:
    routed = route_query("   ", response_language="en")

    assert routed.intent is QueryIntent.EMPTY
    assert deterministic_response(routed.intent, language="en") == "Please enter a question."


@pytest.mark.parametrize(
    "text",
    [
        "Yüklediğim belgeleri konularına göre gruplandır",
        "Hangi belgeleri yükledim?",
        "Group the documents I uploaded by subject",
        "What documents are indexed?",
    ],
)
def test_router_classifies_document_inventory_questions(text: str) -> None:
    routed = route_query(text, response_language="tr")

    assert routed.intent is QueryIntent.DOCUMENT_INVENTORY


def test_exact_bad_phase_4_refusal_is_not_grounded() -> None:
    chat = FakeChatProvider(
        responses=[
            "STATUS: insufficient\n"
            "The provided context does not contain specific information about Phase 4."
        ]
    )
    retrieval = CountingRetrievalService([_result()])
    service = RagService(settings=Settings(), retrieval_service=retrieval, chat_provider=chat)

    answer = service.answer(RagRequest(query="What is Phase 4?"))

    assert answer.grounded is False
    assert answer.insufficient_evidence is True
    assert answer.citations == []
    assert chat.calls == 0


def _result() -> RetrievalResult:
    return RetrievalResult(
        document_id="doc-1",
        chunk_id="chunk-1",
        chunk_index=0,
        content="Phase 3 discusses parsing only.",
        score=0.2,
        page_number=None,
        section_title="Phase 3",
        source_filename="phases.docx",
        source_file_type=SupportedFileType.DOCX,
        source_start_order=0,
        source_end_order=0,
    )
