# GroundNote Roadmap

| Phase | Name | Status |
| --- | --- | --- |
| 0 | Repository foundation and application shell | Complete |
| 1 | Environment verification and Foundry Local discovery | Complete |
| 2 | Configuration, Domain Models, and SQLite Storage | Complete |
| 3 | Secure document validation and parsing | Complete |
| 4 | Hybrid Recursive Chunking and Pre-Embedding Ingestion | Not started |
| 5 | Chunking pipeline and metadata handling | Not started |
| 6 | Embedding provider interface and local embedding persistence | Not started |
| 7 | Retrieval with NumPy cosine similarity | Not started |
| 8 | Foundry Local chat provider and RAG answer generation | Not started |
| 9 | Streamlit study workflow UI | Not started |
| 10 | Polishing, documentation, packaging notes, and final QA | Not started |

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
