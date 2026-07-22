# GroundNote Project State

## Current Release

- Target version: `1.0.0`
- Current phase: Phase 10 — final portfolio, documentation, and publication release
- Phase 10 status: Complete
- Branch: `main`
- Inference: Microsoft Foundry Local only; no cloud fallback
- Primary platform: Windows 11

The 1.0.0 publication scope contains the manually validated Phase 9 correctness, single-file/F5
ownership, document-safety, diagnostics, setup, launcher, and deterministic release changes plus
the Phase 10 publication work. The user authorized one release commit and a normal push to `main`
after validation; no tag or GitHub Release is authorized.

## Implemented Product

### Documents and Storage

- Supports PDF, DOCX, TXT, and Markdown.
- Validates file names, extensions, signatures, compressed size, and format-specific resource
  limits before local embedding.
- Uses SHA-256 exact duplicate detection and collision-resistant managed filenames.
- Preserves PDF page numbers and DOCX/Markdown section metadata where available.
- Stores document metadata, chunks, FTS5 rows, and normalized finite float32 embedding BLOBs in
  SQLite through parameterized repositories and explicit Unit of Work transactions.
- Removes only validated GroundNote-managed copies; original selected files and unrelated files are
  never deletion targets.

### Indexing and Integrity

- Uses deterministic hybrid recursive chunking and bounded ordered embedding batches.
- Keeps local model inference outside SQLite write transactions.
- Requires complete chunks, compatible embeddings, document model metadata, and one valid FTS row
  per chunk before committing Ready/`INDEXED`.
- Reconciles interrupted or incomplete indexes to a non-searchable retryable state at bootstrap.
- Uses database-scoped process-local ownership so browser refreshes preserve genuinely active work
  and a true process restart recovers stale transient records.
- Accepts one file at a time; there is no background upload queue or worker.

### Retrieval and RAG

- Combines SQLite FTS5 lexical search with NumPy cosine similarity over local embeddings.
- Applies document/type filters, heading and numbered-term boosts, conservative typo expansion,
  adjacent context, section/title filtering, and named-entity evidence checks.
- Treats retrieved document text as untrusted evidence inside bounded prompts.
- Generates through Foundry Local and validates citation IDs against trusted retrieval metadata.
- Returns citation-free English/Turkish insufficient-evidence responses rather than fabricating an
  answer.
- Routes greetings, invalid input, help, and document inventory locally without unnecessary model
  calls.

### Streamlit Interface

- Chat-first English/Turkish interface with one-file automatic synchronous upload.
- Real indexing stages, Ready status, duplicate handling, retry, and privacy-safe errors.
- Knowledge Base with safe metadata, per-document re-index, confirmed remove, and clear-all.
- Source filters, New chat, session-only conversation messages, and no persistent chat history.
- Balanced, Fast, and Memory saver modes with explicit GroundNote-owned model cleanup.
- Chat and document mutations are blocked while indexing is active.
- Technical details are hidden unless the user explicitly enables the debug toggle.

### Safety and Release Tooling

- Default limits: 50 MB upload, 1,000 PDF pages, 5,000,000 extracted characters, 10,000 chunks,
  200 MB DOCX expansion, 50 MB per member, 100:1 compression ratio, and 2,000 members.
- DOCX parsing validates untrusted ZIP metadata and reads only bounded required XML without
  filesystem extraction.
- Logs and diagnostics exclude full documents, questions, prompts, embeddings, secrets, and raw
  local paths.
- Runtime-only idempotent Windows setup, doctor, loopback launcher, token/PID/port-scoped stop, and
  token-scoped failure cleanup are implemented.
- Portable release building is deterministic, link/path bounded, private-data allowlisted, and
  accompanied by a filename-only SHA-256 sidecar.

## Model Configuration

- Default chat model: `phi-3.5-mini`
- Low-resource chat model: `qwen2.5-0.5b`
- Embedding model: `qwen3-embedding-0.6b`
- Embedding dimension: 1,024
- Embedding dtype: `float32`
- Default embedding batch size: 16

The verified local catalog selected CPU execution-provider variants. No GPU/NPU acceleration claim
is made.

## Measured Performance

Measurements are machine/workload specific:

- `phi-3.5-mini`: 5.85 s load and 0.505 s short response in the candidate benchmark.
- `qwen2.5-0.5b`: 2.64 s load and 0.135 s short response.
- `qwen3-embedding-0.6b`: 2.43 s load, 1.58 s small-batch embedding, 1,024 finite float32 values.
- 121-chunk indexing: 83.833 s total, including 82.300 s embedding; 896.441 MB observed peak
  process RSS.

CPU embedding is the primary observed indexing bottleneck. Synchronous indexing and blocked chat
during indexing are deliberate resource-safety decisions.

## Prior Release-Hardening Validation

The final Phase 9 completion run passed:

- Ruff lint and formatting checks;
- strict mypy over `src`;
- 365 non-Foundry tests with two environment/capability skips;
- 81% total coverage;
- Foundry discovery, fake UI pipeline, and real Foundry UI smoke;
- runtime-only setup dry run, stopped-service setup, and idempotency;
- launcher failure cleanup, HTTP startup, duplicate launch, and scoped stop;
- two identical 151-entry release builds with matching SHA-256 sidecars;
- extraction/setup/start/stop from a path containing spaces; and
- cleanup with Foundry stopped, zero loaded models, and validation ports free.

These results describe the prior 0.9.0 working tree. The final 1.0.0 validation results below
supersede them.

## Phase 10 Deliverables

- Canonical version promotion to `1.0.0`.
- Final public README and implemented architecture diagrams.
- Original redistribution-safe demo handbook and question set.
- Demonstration script and English/Turkish presentation outlines.
- MIT license verification, contribution/security guidance, and GitHub issue/PR templates.
- Privacy-safe real screenshots captured only from the demonstration handbook.
- Updated changelog, roadmap, release/configuration/interface/support documentation, and decisions.
- Full quality, privacy, real Foundry, manual UI, setup, launcher, release, and cleanup validation.
- Exactly one authorized final commit and a normal `main` push after every gate passed.

## Phase 10 Validation

- `uv sync`: Passed; package metadata and `uv.lock` resolve GroundNote `1.0.0`.
- `uv run python -m groundnote --version`: Passed with `1.0.0`.
- Ruff lint/format and strict mypy: Passed; 175 files formatted and 99 source files typed.
- Full non-Foundry suite: 363 passed, two Windows environment/capability tests skipped.
- Coverage: 363 passed, two skipped, 83% total coverage.
- Foundry check: CLI `0.10.2`, Windows SDK `1.2.3`, 46 aliases, required CPU variants cached,
  and no model download.
- Fake UI pipeline: Passed with indexing, citation, duplicate, persistence, and insufficient
  evidence behavior.
- Real Foundry UI smoke: Passed with local embeddings, grounded English/Turkish answers, trusted
  citations, citation-free insufficient evidence, no cleanup warning, and zero loaded models.
- Real safe-document UI smoke: 14 chunks indexed; Ready required complete integrity; a grounded
  answer cited `Data Quality Rules`; the unsupported satellite question returned no sources; New
  chat preserved the index; English/Turkish UI, re-index, and remove succeeded.
- Three real screenshots were captured from the original fictional handbook with no personal path,
  account, secret, or private document content.
- PowerShell parser: Passed for every script.
- Setup dry run and two stopped-Foundry runtime-only setup runs: Passed; existing marker preserved,
  no development packages installed, and temporary data removed.
- Launcher: HTTP 200, duplicate detection, token/PID/port-scoped stop, and metadata-write failure
  cleanup passed with ports and session metadata removed.
- Release: two 153-entry 1.0.0 archives produced the same SHA-256; the sidecar matched; required
  public/runtime files were present; prohibited/private members were absent.
- Extracted release: runtime-only setup, doctor, launch, HTTP health, and scoped stop passed from a
  path containing spaces.
- Cleanup: temporary databases, managed demo copies, logs, release ZIP/checksum files, extraction
  trees, environments, coverage output, session metadata, listeners, and GroundNote-owned model
  activity were removed.

## Known Limitations

- CPU embedding can be slow for medium and large documents.
- Indexing is synchronous, accepts one document at a time, and disables chat while active.
- No OCR, persistent background queue, active cancellation, or parallel model execution.
- No persistent conversation history, multi-user accounts, cloud sync, or external integrations.
- A failed replacement re-index cannot retain the prior complete vector version.
- No signed native installer, bundled model, or automatic updater.
- Windows setup/launcher/release behavior has the strongest validation; macOS is best effort.
- Foundry Local is preview software and its SDK, CLI, and catalog may change.

## Environment Facts

- OS: Windows 11 Pro, 64-bit
- Managed Python: `3.11.15`
- uv: `0.11.29`
- Foundry Local CLI: `0.10.2`
- Windows SDK: `foundry-local-sdk-winml 1.2.3`

Machine-identifying hostnames, user-profile paths, and private document names are intentionally not
recorded.

## Next Step

There is no next implementation phase in the approved portfolio roadmap. Future enhancements should
be requested explicitly and treated as post-1.0 work. Tags, GitHub Releases, native installer
publication, and any external deployment remain unauthorized without a new explicit request.
