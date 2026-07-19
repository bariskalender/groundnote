# GroundNote Project Specification

## Purpose

GroundNote is a private, offline-first study assistant that helps a learner ask questions about
their own documents. It will use local document parsing, local embeddings, local retrieval, and a
local language model through Microsoft Foundry Local.

## Target Users

- Students who want to study from lecture notes, PDFs, and written materials.
- Beginners who need a simple local tool, not an enterprise knowledge platform.
- Users who care about privacy and do not want their study materials sent to cloud services.

## Functional Requirements

- Import supported study documents into a local library.
- Detect duplicate documents with SHA-256 hashing.
- Extract text from supported files while preserving useful metadata.
- Split documents into searchable chunks.
- Generate and persist embeddings locally.
- Retrieve relevant chunks with NumPy cosine similarity.
- Answer user questions using retrieved context and Foundry Local chat models.
- Cite source filename and page number metadata when available.
- Provide a simple Streamlit desktop-style interface.
- Answer in the same language as the user's question.

## Non-Functional Requirements

- Work offline after required local tools and models are installed.
- Keep documents, prompts, embeddings, logs, and generated answers on the user's machine.
- Use SQLite for persistence.
- Use parameterized SQL and transactions for data-changing operations.
- Keep implementation readable and maintainable.
- Prefer conservative dependencies.
- Target Windows 11 first and keep macOS compatibility where practical.

## Supported File Types

MVP support:

- PDF
- DOCX
- TXT
- Markdown

Non-MVP:

- OCR for scanned documents
- Images
- Audio or video
- Cloud document sources

## Offline And Privacy Expectations

GroundNote must not upload user documents, prompts, embeddings, logs, or answers to external
services. Foundry Local is the required local model runtime. The application must not silently
fall back to Azure OpenAI, OpenAI APIs, or another cloud provider.

## Architecture Boundaries

- `config`: Settings and environment loading.
- `domain`: Core project entities and value objects.
- `storage`: SQLite connection management, migrations, repositories, and transaction handling.
- `documents`: File ingestion and text extraction.
- `chunking`: Document chunking.
- `embeddings`: Embedding provider interfaces and local model integration.
- `retrieval`: Similarity search and result ranking.
- `generation`: Chat provider interfaces and answer generation.
- `ui`: Streamlit UI helpers.
- `utils`: Shared utilities.

Foundry Local-specific code must live behind provider interfaces so SDK changes remain isolated.

## MVP Features

- Local document ingestion for supported file types.
- Local chunking, embedding, storage, retrieval, and answer generation.
- Simple Streamlit interface for upload, indexing status, chat, and citations.
- Clear setup and troubleshooting documentation.

Implemented foundation so far:

- Typed settings and explicit application bootstrap.
- Privacy-aware structured logging helpers.
- Domain models for documents, chunks, retrieval results, and answers.
- SQLite schema migrations and repository foundation.
- Float32 BLOB embedding serialization.
- Secure validation, hashing, duplicate pre-checking, and text extraction for PDF, DOCX, TXT, and
  Markdown.
- Deterministic hybrid recursive chunking and transaction-safe pre-embedding ingestion.
- Local Foundry embedding generation, normalized SQLite vector persistence, and NumPy semantic
  retrieval.

## Non-MVP Features

- OCR
- Multi-user accounts
- Cloud sync
- Hosted deployment
- Browser extensions
- Advanced admin dashboards
- External integrations
- Fine-tuning
