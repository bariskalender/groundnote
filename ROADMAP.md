# GroundNote Roadmap

GroundNote follows a completed ten-phase portfolio roadmap. Corrective stabilization work is
consolidated into the phase that owns the final behavior; temporary internal subphase labels are not
part of the public release plan.

| Phase | Name | Status |
| --- | --- | --- |
| 0 | Repository foundation and application shell | Complete |
| 1 | Foundry Local discovery and provider interfaces | Complete |
| 2 | Configuration, domain models, and SQLite storage | Complete |
| 3 | Secure document validation and parsing | Complete |
| 4 | Hybrid recursive chunking and pre-embedding ingestion | Complete |
| 5 | Local embedding, indexing, and semantic retrieval | Complete |
| 6 | Grounded RAG generation and citations | Complete |
| 7 | Streamlit upload, indexing, chat, and product stabilization | Complete |
| 8 | Knowledge Base and session management | Complete |
| 9 | Packaging, correctness, security, and release hardening | Complete |
| 10 | Portfolio documentation and publication release | Complete |

## Completed Scope

### Foundation and Local Models

- Python 3.11 src-layout project with uv, Ruff, mypy, pytest, and Streamlit.
- Microsoft Foundry Local discovery, official alias inspection, and provider-neutral contracts.
- Local chat and embedding candidate benchmarks with fake-provider unit coverage.
- No cloud model fallback, telemetry, or external vector database.

### Local Document Knowledge Base

- Typed settings and explicit bootstrap with platform-local data directories.
- SQLite migrations, parameterized repositories, short Unit of Work transactions, and FTS5.
- Finite normalized float32 embedding BLOB storage with model/version metadata.
- PDF, DOCX, TXT, and Markdown validation and bounded local parsing.
- SHA-256 duplicate detection, validated managed copies, and safe removal behavior.
- Deterministic recursive chunking with source filename, page, section, and order metadata.

### Retrieval and Grounded Answers

- Foundry Local embedding indexing in bounded ordered batches.
- NumPy cosine similarity and SQLite FTS5 hybrid retrieval.
- Section/title and named-entity evidence checks.
- Bounded prompts that treat document text as untrusted evidence.
- Turkish/English response routing, citation validation, and evidence-based refusal.
- No persistent conversation history or topic-specific factual shortcuts.

### Streamlit Product

- Chat-first interface with one-file automatic synchronous upload.
- Safe indexing stages, Ready integrity status, duplicates, retries, and source filters.
- Local Knowledge Base with re-index, confirmed remove, and clear-all controls.
- New chat clears session-only messages while preserving indexed documents.
- Performance modes, mode-aware cleanup, localized Foundry state, and opt-in technical details.
- Browser refresh preserves genuinely active indexing ownership and cannot expose a partial index.

### Release Hardening

- PDF page/text/chunk bounds and DOCX ZIP/XML expansion/path protections.
- One GroundNote-owned chat lifecycle and embedding-before-chat cleanup.
- Runtime-only idempotent Windows setup, privacy-safe doctor, loopback launcher, and scoped stop.
- Deterministic portable ZIP with SHA-256, path/link validation, and private/generated exclusions.
- Full regression, coverage, real Foundry, setup, launcher, path-with-spaces extraction, and release
  archive validation.

## Version 1.0.0 Portfolio Release

Phase 10 promoted the project to 1.0.0 and added the final public README, implemented-architecture
diagrams, original demonstration handbook/questions, demo script, English/Turkish presentation
outlines, contribution/security guidance, GitHub templates, screenshots, and final publication
records. Quality, privacy, real-model, setup, launcher, manual, and release-artifact checks passed
before the final publication commit.

## Known 1.0.0 Limitations

- CPU embedding latency is the primary observed indexing bottleneck.
- Indexing is synchronous; there is no persistent background queue or cancellation service.
- One document is uploaded at a time, and chat is unavailable during indexing.
- OCR is not implemented; scanned/image-only PDFs are unsupported.
- Chat history is session-only and is not persisted.
- Failed re-indexing does not preserve the prior complete vector version.
- Models and Foundry Local are external prerequisites and are not bundled.
- There is no native signed installer or automatic updater.
- Launcher and portable-release validation are Windows-focused; macOS support is best effort.

## Future Enhancements

These items are ideas beyond the completed 1.0.0 portfolio scope, not promised features:

- OCR for scanned PDFs with an explicit privacy/resource design.
- Cancellable background indexing with durable job ownership and restart recovery.
- Hardware-acceleration evaluation across current official Foundry Local variants.
- Old-vector preservation during a failed replacement re-index.
- Broader macOS and clean-machine validation.
- A signed native installer, upgrade/rollback behavior, and automatic-update design.
- Optional persistent conversation history with clear retention and deletion controls.
