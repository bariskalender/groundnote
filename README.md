# GroundNote

Private, Offline RAG Study Assistant powered by Microsoft Foundry Local

## About the Project

GroundNote is a local document assistant mainly designed for university students. The goal is to
help students study from lecture notes, course documents, and personal study materials without
sending those files to a cloud AI service.

Users can upload PDF, DOCX, TXT, and Markdown files, index them locally, manage the local
Knowledge Base, and ask questions about their contents through the Streamlit interface.

## Why GroundNote?

- Study from lecture notes and course documents.
- Keep documents private on the local computer.
- Avoid sending personal study materials to cloud AI services.
- Receive answers grounded in uploaded documents.

## Current Progress

- Project structure.
- Python 3.11 and uv environment.
- Minimal Streamlit application shell.
- Microsoft Foundry Local installation and verification.
- Local chat model provider.
- Local embedding provider.
- Model benchmark scripts.
- Typed settings and explicit application bootstrap.
- SQLite schema migrations and repository foundation.
- Secure document validation and text extraction for PDF, DOCX, TXT, and Markdown.
- Deterministic hybrid recursive chunking and pre-embedding ingestion.
- Local embedding indexing and semantic retrieval.
- Grounded single-turn RAG answer generation with citations.
- Chat-first Streamlit document upload, indexing, grounded Q&A, session history, and trusted
  citation interface.
- Hybrid lexical/vector retrieval with conservative typo-tolerant search.
- Multiple-file upload, English/Turkish UI text, New chat, and performance modes.
- Automatic sequential processing after file selection with compact per-document status and retry.
- Gear-based settings and Streamlit-safe Windows logging without browser tracebacks.
- Phase 7.2 router hardening for empty, unclear, greeting, thanks, and help inputs before model
  calls.
- Repetition protection, compact citations, lower RAG context budget, warm embedding reuse, and
  safer image-only PDF handling.
- Minimal confirmed document removal, metadata-based document inventory answers, hidden-by-default
  debug details, and mode-aware resource cleanup.
- Section-title-aware retrieval, stronger unsupported-question shortcuts, cleaner answer
  formatting, and friendly busy-state handling.
- A localized Knowledge Base with document metadata, confirmed remove and clear-all controls, and
  sequential per-document re-indexing.
- Safe duplicate and insufficient-evidence presentation.
- Unit tests.
- Ruff and mypy checks.

## Current Model Setup

- Default chat model: `phi-3.5-mini`
- Low-resource fallback: `qwen2.5-0.5b`
- Embedding model: `qwen3-embedding-0.6b`

The default model may change after future testing.

## Benchmark Summary

| Model | Purpose | Load Time | Response / Embedding Time | Memory |
| --- | --- | ---: | ---: | ---: |
| phi-3.5-mini | Default chat | 5.85 s | 0.505 s | ~3.36 GB RSS |
| qwen2.5-0.5b | Low-resource chat | 2.64 s | 0.135 s | ~620 MB RSS |
| qwen3-embedding-0.6b | Embeddings | 2.43 s | 1.58 s batch | 1024 dimensions |

These measurements were collected on the current development machine and may differ on other
hardware.

## Planned Features

- Additional packaging and final demonstration polish.

## Technology Stack

- Python 3.11
- Streamlit
- Microsoft Foundry Local
- SQLite
- NumPy
- Pydantic
- pytest
- Ruff
- mypy
- uv

## Local Development

```powershell
uv sync
uv run streamlit run src/groundnote/app.py
uv run ruff check .
uv run mypy src
uv run pytest -m "not foundry"
```

## Project Status

- Phase 0 completed.
- Phase 1 completed.
- Phase 2 completed.
- Phase 3 completed.
- Phase 4 completed.
- Phase 5 completed locally.
- Phase 6 completed locally.
- Pre-Phase 7 UI readiness audit completed locally.
- Phase 7 completed locally.
- Phase 7.1 stabilization completed locally.
- Phase 7.1.1 automatic-upload and Windows reliability patch completed locally.
- Phase 7.2 performance, answer quality, router, and indexing optimization completed locally.
- Phase 7.2.1 real-test stability, minimal document removal, inventory routing, and resource
  control patch completed locally.
- Phase 7.2.2 section retrieval, answer completion, and UI state fixes completed locally.
- Phase 8 Knowledge Base and lightweight session management completed locally.
- Secure validation and text extraction are implemented for PDF, DOCX, TXT, and Markdown.
- Parsed documents are chunked and persisted with `PENDING_EMBEDDING` status.
- Local embeddings are generated and persisted for indexed documents.
- Semantic retrieval returns ranked chunks with citation metadata.
- Grounded single-turn RAG answer generation is implemented with citation validation.
- The Streamlit interface automatically processes selected files sequentially, shows compact safe
  document states, supports per-document retry, and provides session-only chat, trusted citations,
  compact source display, and insufficient-evidence results.
- Invalid short inputs do not call retrieval or local models. Low-confidence retrieval returns
  insufficient evidence without chat generation. Obvious out-of-domain named-entity questions also
  fail fast when retrieved chunks do not contain the requested entities.
- Persistent database-backed conversation memory is intentionally not implemented.
- Remove, clear-all, and per-document re-index controls change only GroundNote's local database
  index; they never delete the original source files.

See `docs/supported-documents.md`, `docs/document-processing.md`, `docs/chunking-strategy.md`,
`docs/pre-embedding-ingestion.md`, `docs/embedding-and-indexing.md`, and
`docs/semantic-retrieval.md`, `docs/rag-generation.md`, `docs/prompt-safety.md`,
`docs/citations-and-language.md`, `docs/streamlit-interface.md`, `docs/demo-workflow.md`,
`docs/phase-7-1-stabilization.md`, `docs/phase-7-2-optimization.md`, and
`docs/phase-7-2-1-real-test-stability.md`, and
`docs/phase-7-2-2-section-retrieval-ui-stability.md`, and
`docs/phase-8-knowledge-base-session-management.md` for the current behavior and limitations.

## Privacy

No cloud AI API is currently used. Model inference runs through Microsoft Foundry Local.
First-time model downloads require internet, while cached inference is intended to work locally.
User documents must not be committed to Git.

Local models can still make mistakes. Users should verify high-stakes answers against the cited
source documents.

The interface supports English and Turkish. Answers follow the question language by default, with
an optional session setting for English or Turkish. Chat history is session-only.

## License

MIT License.
