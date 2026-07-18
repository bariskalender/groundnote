# GroundNote

Private, Offline RAG Study Assistant powered by Microsoft Foundry Local

## About the Project

GroundNote is a local document assistant mainly designed for university students. The goal is to
help students study from lecture notes, course documents, and personal study materials without
sending those files to a cloud AI service.

In the planned application, users will upload PDF, DOCX, TXT, and Markdown files, then ask
questions about the contents of those documents. GroundNote is still under development. The final
RAG workflow is not complete yet.

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

- Drag-and-drop document upload.
- PDF, DOCX, TXT, and Markdown support.
- Local SQLite knowledge base.
- Hybrid recursive chunking.
- Semantic search using embeddings and cosine similarity.
- Source filename and page number display.
- Document deletion and re-indexing.
- English interface.
- Answers in the same language as the user question.

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
- Phase 2 not started.
- Document ingestion is not implemented yet.
- SQLite storage is not implemented yet.
- Retrieval and RAG pipeline are not implemented yet.

## Privacy

No cloud AI API is currently used. Model inference runs through Microsoft Foundry Local.
First-time model downloads require internet, while cached inference is intended to work locally.
User documents must not be committed to Git.

## License

MIT License.
