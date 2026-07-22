# GroundNote

Private, Offline RAG Study Assistant powered by Microsoft Foundry Local

Current pre-release version: **0.9.0**

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

- Full native installer evaluation after the portable release workflow is proven.
- Final demonstration and portfolio polish.

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

## Requirements

- Windows 11 (primary target).
- Microsoft Foundry Local CLI: `winget install Microsoft.FoundryLocal`.
- uv: `winget install --id=astral-sh.uv -e`.
- Enough disk space for selected local models; models are not bundled with GroundNote.
- Internet for initial dependency/model downloads; cached inference remains local.

Python 3.11 is managed by uv, so a separate system Python installation is not required.

## Windows Setup

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_windows.ps1
```

Setup is idempotent. It synchronizes locked dependencies, creates missing application directories,
initializes/migrates SQLite, and runs the doctor. It does not replace existing user data and does
not download Foundry models. Use `-DryRun` to inspect the workflow without changing the environment.

## Environment Check

```powershell
powershell -ExecutionPolicy Bypass -File scripts/doctor.ps1
```

The doctor reports `OK`, `Warning`, or `Error` for the runtime, configuration, local data, SQLite,
Foundry Local, cached required models, Streamlit port, application import, and Git cleanliness. It
does not start Streamlit, load/download models, or print private paths and secrets.

## Start and Stop

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start_groundnote.ps1
powershell -ExecutionPolicy Bypass -File scripts/stop_groundnote.ps1
```

The launcher binds to `127.0.0.1:8501`, starts Foundry when needed, validates readiness, prints the
URL, and opens the browser. If 8501 belongs to another app, it selects the first available local
port through 8510. Duplicate launches report the existing instance. The stop script validates PID,
port, and a random launcher token, so it never broadly kills Python processes.

Foundry is left unchanged on normal stop because another application may share it. To explicitly
stop Foundry too, run `scripts/stop_groundnote.ps1 -StopFoundry`.

## Troubleshooting

- Run `scripts/doctor.ps1` first; a non-zero exit code means action is required.
- If Foundry is stopped, run `foundry server start`. CLI `0.10.2` uses `server` commands.
- The doctor reports missing aliases; models are downloaded only by an explicit
  `foundry model download <alias>` command.
- OCR is not supported; scanned PDFs need searchable text.
- Browser stack traces and technical details remain hidden by default.

## Local Development

```powershell
uv sync
uv run streamlit run src/groundnote/app.py
uv run ruff check .
uv run mypy src
uv run pytest -m "not foundry"
```

Normal users should prefer `scripts/start_groundnote.ps1` so duplicate detection and scoped stop
metadata are available.

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
- Phase 8.1 Knowledge Base action and operation-state stabilization completed locally.
- Phase 9 packaging and release preparation completed locally.
- Phase 9.1A grounding correctness, interrupted-index recovery, and managed-copy safety completed
  locally.
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
- Remove and clear-all delete GroundNote's database records and only the validated managed copies
  created inside GroundNote's document directory. They never delete the original selected files or
  unrelated local files. Re-index reuses the existing chunks and managed copy.
- A document is Ready only when its chunks, compatible float32 embeddings, model metadata, and FTS
  rows form a complete committed index. Interrupted or inconsistent documents are excluded from
  retrieval and can be explicitly re-indexed.

See `docs/supported-documents.md`, `docs/document-processing.md`, `docs/chunking-strategy.md`,
`docs/pre-embedding-ingestion.md`, `docs/embedding-and-indexing.md`, and
`docs/semantic-retrieval.md`, `docs/rag-generation.md`, `docs/prompt-safety.md`,
`docs/citations-and-language.md`, `docs/streamlit-interface.md`, `docs/demo-workflow.md`,
`docs/phase-7-1-stabilization.md`, `docs/phase-7-2-optimization.md`, and
`docs/phase-7-2-1-real-test-stability.md`, and
`docs/phase-7-2-2-section-retrieval-ui-stability.md`, and
`docs/phase-8-knowledge-base-session-management.md`, `docs/phase-9-packaging-release.md`,
`docs/packaging-strategy.md`, and `docs/release-checklist.md` for current behavior and limitations.

## Privacy

No cloud AI API is currently used. Model inference runs through Microsoft Foundry Local.
First-time model downloads require internet, while cached inference is intended to work locally.
User documents must not be committed to Git.

Local models can still make mistakes. Users should verify high-stakes answers against the cited
source documents.

The interface supports English and Turkish. Answers follow the question language by default, with
an optional session setting for English or Turkish. Chat history is session-only.

GroundNote contains no telemetry or analytics. Setup, launcher, doctor, and archive tools do not
upload documents, prompts, answers, embeddings, logs, or configuration. The portable archive
excludes local databases, documents, logs, models, caches, `.env`, and test artifacts.

## Portable Release Archive

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_release_archive.ps1
```

This produces `dist/groundnote-0.9.0.zip` with runtime source, locked dependencies, setup/launcher
scripts, configuration example, documentation, changelog, and license. Foundry models and user data
are never bundled. See `docs/packaging-strategy.md` and `docs/release-checklist.md`.

## License

MIT License.
