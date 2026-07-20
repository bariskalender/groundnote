from __future__ import annotations

from groundnote.domain import SupportedFileType
from groundnote.rag.models import Citation, PromptBundle, RagAnswer, RagContextItem, RagRequest


def test_rag_models_hide_private_text_in_repr() -> None:
    secret = "PRIVATE RAG QUERY OR ANSWER"
    context = RagContextItem(
        citation_id="S1",
        document_id="doc",
        chunk_id="chunk",
        chunk_index=0,
        content=secret,
        score=0.8,
        source_filename="notes.txt",
        source_file_type=SupportedFileType.TXT,
        page_number=None,
        section_title=None,
        source_start_order=0,
        source_end_order=0,
    )
    answer = RagAnswer(
        answer=secret,
        citations=[
            Citation(
                citation_id="S1",
                document_id="doc",
                chunk_id="chunk",
                source_filename="notes.txt",
                source_file_type=SupportedFileType.TXT,
                page_number=None,
                section_title=None,
                chunk_index=0,
                display_label="notes.txt — chunk 1",
            )
        ],
        grounded=True,
        insufficient_evidence=False,
        response_language="en",
        model="fake",
        prompt_version="grounded-rag-v1",
        retrieved_count=1,
        used_context_count=1,
        warnings=[],
        duration_ms=1.0,
    )
    rendered = "\n".join(
        [
            repr(RagRequest(query=secret)),
            repr(context),
            repr(answer),
            repr(
                PromptBundle(
                    system_prompt=secret,
                    user_prompt=secret,
                    prompt_version="v",
                    allowed_citation_ids=[],
                )
            ),
        ]
    )

    assert secret not in rendered
