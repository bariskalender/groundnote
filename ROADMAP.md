# GroundNote Roadmap

| Phase | Name | Status |
| --- | --- | --- |
| 0 | Repository foundation and application shell | Complete |
| 1 | Environment verification and Foundry Local discovery | Complete |
| 2 | Configuration, logging, and application settings | Not started |
| 3 | SQLite schema and storage layer | Not started |
| 4 | Document ingestion for PDF, DOCX, TXT, and Markdown | Not started |
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
