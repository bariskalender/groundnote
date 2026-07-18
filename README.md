# GroundNote

Private, Offline RAG Study Assistant.

GroundNote is an early-development local study assistant. The goal is to help users ask questions
about their own documents with local retrieval and Microsoft Foundry Local models.

The RAG system does not work yet. Phase 0 only creates the repository structure, project
documentation, dependency configuration, basic quality tooling, and a minimal Streamlit app shell.

## Project Goals

- Keep study documents and generated data on the user's machine.
- Use local embeddings and local chat models through Microsoft Foundry Local.
- Provide a simple Streamlit interface for learning-focused document Q&A.
- Prefer readable, maintainable code over unnecessary complexity.

## Installation

Python 3.11 and `uv` are required.

```powershell
uv sync
uv run streamlit run src/groundnote/app.py
```

If `uv` is not installed, install it from the official Astral instructions:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Privacy

GroundNote is designed to be privacy-first and local-first. The application must not upload user
documents, prompts, embeddings, or logs to GitHub, cloud model APIs, or external services without
explicit user approval.
