# GroundNote Roadmap

| Phase | Name | Status |
| --- | --- | --- |
| 0 | Repository foundation and application shell | Complete |
| 1 | Environment verification and Foundry Local discovery | Complete |
| 2 | Configuration, Domain Models, and SQLite Storage | Complete |
| 3 | Secure document validation and parsing | Complete |
| 4 | Hybrid Recursive Chunking and Pre-Embedding Ingestion | Complete |
| 5 | Embedding, Indexing, and Semantic Retrieval | Complete |
| 6 | Foundry Local chat provider and RAG answer generation | Complete |
| Audit | Pre-Phase 7 UI readiness audit | Complete |
| 7 | Streamlit Upload, Indexing, and Chat Interface | Complete |
| 7.1 | Product Stabilization, Retrieval Reliability, Performance, and Chat UX Rebuild | Complete |
| 8 | Knowledge Base Management, Delete, Re-index, and Index Controls | Not started |

## Phase 0 Acceptance Notes

- Create the repository structure and required governance documents.
- Configure Python packaging, dependencies, Ruff, mypy, and pytest.
- Add a minimal Streamlit app shell.
- Do not implement document parsing, embeddings, retrieval, Foundry Local integration, or RAG.

## Phase 1 Acceptance Notes

- Foundry Local CLI status is known and documented.
- Foundry Local SDK initializes and lists the current model catalog.
- Provider interfaces and Foundry-backed provider wrappers exist.
- Fake providers support normal unit tests without model downloads.
- Lightweight chat and embedding candidates were benchmarked sequentially.
- No document ingestion, SQLite storage, retrieval, or Streamlit chat was implemented.

## Phase 2 Acceptance Notes

- Typed settings load from defaults, `.env`, and `GROUNDNOTE_` environment variables.
- Structured logging is configured explicitly and redacts sensitive fields.
- Domain models exist for documents, chunks, retrieval results, and answers.
- SQLite migrations create `documents`, `document_chunks`, and `application_metadata`.
- Embeddings serialize as finite one-dimensional float32 BLOB values.
- Document and vector repositories work through a transaction-aware Unit of Work.
- Bootstrap initializes settings, logging, directories, and database schema.
- No parsing, ingestion, retrieval, RAG generation, or Streamlit chat was implemented.

## Phase 3 Acceptance Notes

- Secure validation works for PDF, DOCX, TXT, and Markdown file extensions.
- Safe stored filenames are generated with UUID prefixes and traversal protection.
- SHA-256 hashes are calculated from original file bytes using streaming reads.
- Exact duplicate pre-checks use the existing document repository before parsing.
- PDF text extraction preserves 1-based page numbers and reports blank/scanned-page limitations.
- DOCX extraction preserves headings, paragraphs, lists, and simple table text with null page
  numbers.
- TXT supports UTF-8 and UTF-8 with BOM while rejecting binary-looking text files.
- Markdown headings, lists, code blocks, Unicode, and inert HTML text are preserved.
- Parser registry and document processing service are independent of Streamlit and Foundry Local.
- No chunking, embedding generation, indexing, semantic retrieval, RAG generation, or final chat UI
  was implemented.

## Phase 4 Acceptance Notes

- Added deterministic hybrid recursive chunking with paragraph, sentence, whitespace, and hard
  split fallbacks.
- Preserved page numbers, section titles, source order metadata, chunk indexes, chunking version,
  and approximate token estimates.
- Added overlap only between compatible chunks and avoided overlap across PDF pages or unrelated
  headings.
- Added safe short-fragment merging with warnings when boundaries prevent a safe merge.
- Added transaction-safe pre-embedding ingestion for PDF, DOCX, TXT, and Markdown.
- Persisted document metadata and chunks with `PENDING_EMBEDDING` status and null embedding fields.
- No embeddings, Foundry model calls, semantic retrieval, RAG generation, or final upload/chat UI
  were implemented.

## Phase 5 Acceptance Notes

- Added local embedding validation, normalization, and batch generation through Foundry Local.
- Stored normalized float32 embeddings and embedding metadata in SQLite.
- Added transaction-safe document indexing with `PENDING_EMBEDDING -> INDEXING -> INDEXED` status
  flow.
- Added safe force re-indexing and embedding clearing foundations.
- Added NumPy cosine-similarity semantic retrieval with top-k, candidate limits, minimum score, and
  document/file/page filters.
- Returned ranked chunks with filename, file type, page, section, source order, score, and metadata.
- No chat model calls, RAG answer generation, final upload/chat UI, external vector database, or
  cloud API were implemented.

## Phase 6 Acceptance Notes

- Added grounded single-turn RAG answer generation using retrieved chunks and Foundry Local chat.
- Added RAG query validation, Turkish/English response-language handling, bounded context assembly,
  citation IDs, citation validation, and deterministic insufficient-evidence responses.
- Added prompt-injection defenses that keep retrieved document text out of system instructions and
  treat source content as untrusted evidence.
- Added local-only chat provider fallback through the loopback Foundry daemon for preview SDK
  runtime issues.
- Added RAG unit, integration, privacy, citation, prompt-safety, and fake-provider pipeline tests.
- Added RAG generation, prompt-safety, and citations/language documentation.
- No final Streamlit chat UI, persistent conversation memory, cloud API, external vector database,
  or Phase 7 work was implemented.

## Pre-Phase 7 UI Readiness Audit Notes

- Verified the Phases 0-6 backend foundation before Streamlit upload, indexing, Knowledge Base,
  and chat UI work.
- Fixed indexing transaction duration so local embedding model loading and generation no longer
  hold a SQLite write transaction open.
- Confirmed startup remains lightweight and does not load chat or embedding models.
- Confirmed uploaded-file helpers, document validation, duplicate detection, parsing, chunking,
  indexing, retrieval, RAG generation, citations, privacy protections, and logging are ready for a
  Phase 7 UI adapter.
- Added `docs/audits/pre-phase-7-ui-readiness-audit.md`.
- At audit completion, Phase 7 had not started.

## Phase 7 Acceptance Notes

- Added a wide Streamlit application with Documents and Ask GroundNote navigation.
- Added explicit one-file upload confirmation for PDF, DOCX, TXT, and Markdown with aligned 50 MB
  Streamlit and backend limits.
- Connected safe uploaded-byte writing, duplicate detection, ingestion, chunking, persistence, local
  embedding indexing, document status, RAG answers, and trusted citations through high-level
  workflows.
- Added indexed-document and file-type source filters without UI SQL or direct provider calls.
- Added deterministic safe error mapping, duplicate presentation, insufficient-evidence behavior,
  and local-model lifecycle feedback.
- Added controlled session state containing only safe latest-result data; no persistent or
  history-aware chat was added.
- Verified fake-provider and real Foundry Local UI-backend flows, Streamlit application behavior,
  rerun safety, duplicate handling, and model cleanup.
- Added `docs/streamlit-interface.md` and `docs/demo-workflow.md`.
- No deletion UI, re-index UI, full Knowledge Base management, OCR, cloud inference, or Phase 8
  work was implemented.

## Phase 7.1 Acceptance Notes

- Removed pre-scoring SQL candidate starvation so long documents and later documents remain
  searchable before final ranking limits are applied.
- Added SQLite FTS5 lexical search with hybrid ranking, heading and numbered-term boosts,
  conservative typo expansion, and adjacent-context support.
- Added deterministic routing for greetings, thanks, and app help so simple messages bypass
  retrieval and local model loading.
- Added a stronger supported/insufficient generation contract with citation-free insufficient
  evidence.
- Changed the default model lifecycle to keep models warm during an interactive session while
  preserving Memory saver and manual unload behavior.
- Rebuilt Streamlit around a chat-first main view with sidebar upload, source filters, performance
  mode, Turkish/English UI text, session-only chat history, New chat, compact citations, and
  recoverable operation state.
- Added multiple-file upload and minimal retry indexing without implementing Phase 8 Knowledge Base
  management.
