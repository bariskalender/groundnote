# GroundNote Decisions

## ADR-0001: Use Python 3.11

- Status: Accepted
- Date: 2026-07-18

GroundNote will target Python 3.11. This matches the project requirement and gives a stable,
well-supported runtime for Streamlit, SQLite, NumPy, and local model integration work.

## ADR-0002: Use Streamlit For The UI

- Status: Accepted
- Date: 2026-07-18

GroundNote will use Streamlit for the user interface. Streamlit is suitable for a local desktop
study assistant because it keeps the UI simple, fast to iterate on, and Python-native.

## ADR-0003: Use SQLite For Local Persistence

- Status: Accepted
- Date: 2026-07-18

GroundNote will use SQLite for metadata, chunks, and embeddings. SQLite keeps the application
local-first, simple to install, and appropriate for a single-user study tool.

## ADR-0004: Use NumPy Cosine Similarity For Retrieval

- Status: Accepted
- Date: 2026-07-18

GroundNote will start with NumPy cosine similarity instead of a separate vector database. This
keeps the MVP understandable and avoids adding infrastructure before it is needed.

## ADR-0005: Use uv For Dependency Management

- Status: Accepted
- Date: 2026-07-18

GroundNote will use `uv` with `pyproject.toml`. This supports fast, reproducible local setup.
`uv.lock` will be generated when `uv` is available.

## ADR-0006: Do Not Use Cloud Providers

- Status: Accepted
- Date: 2026-07-18

GroundNote must not silently use Azure OpenAI, OpenAI APIs, or another cloud provider. Chat,
embeddings, documents, prompts, and logs must remain local unless the user explicitly approves a
different direction in a future conversation.

## ADR-0007: Use Project-Local uv Runtime Directories During Setup

- Status: Accepted
- Date: 2026-07-18

The formatted Windows environment had conflicts in the default `uv` cache path and access issues
in the default managed Python path. Phase 0 uses project-local `.uv-cache` and `.uv-python`
directories so setup and verification can proceed without changing broader user-profile state.

## ADR-0008: Use Foundry Local SDK WinML On Windows

- Status: Accepted
- Date: 2026-07-18

GroundNote uses `foundry-local-sdk-winml` on Windows and `foundry-local-sdk` only on macOS through
mutually exclusive environment markers. The installed Windows SDK version is `1.2.3`. The SDK is
isolated behind provider interfaces so preview API changes remain contained.

## ADR-0009: Use SDK-Selected CPU Variants For Initial Benchmarks

- Status: Accepted
- Date: 2026-07-18

The CLI catalog lists GPU as the default hardware target for the Phase 1 aliases, but the
project-local SDK benchmark resolved and ran CPU variants for `phi-3.5-mini`, `qwen2.5-0.5b`, and
`qwen3-embedding-0.6b`. This is conservative and reliable on the development machine. GPU
availability was detected, but no GPU-specific alias or variant was forced in Phase 1.

## ADR-0010: Keep Initial Model Defaults

- Status: Accepted
- Date: 2026-07-18

Benchmarks showed both chat candidates can answer a trivial prompt, and the embedding candidate
returns finite 1024-dimensional float32 vectors. GroundNote keeps `phi-3.5-mini` as the default
chat model, `qwen2.5-0.5b` as the low-resource fallback, and `qwen3-embedding-0.6b` for
embeddings.

## ADR-0011: Use Pydantic Settings With Explicit Bootstrap

- Status: Accepted
- Date: 2026-07-18

GroundNote uses `pydantic-settings` for typed configuration and `platformdirs` for default local
data paths. Importing settings does not create directories; directory and database initialization
run only through explicit bootstrap.

## ADR-0012: Use Lightweight SQLite Migrations And Unit Of Work

- Status: Accepted
- Date: 2026-07-18

GroundNote uses a small versioned SQL migration runner instead of Alembic. SQLite repositories do
not commit on every method; transaction boundaries are controlled by `SQLiteUnitOfWork` so future
document replacement and re-indexing workflows can be atomic.

## ADR-0013: Store Embeddings As float32 BLOB Values

- Status: Accepted
- Date: 2026-07-18

GroundNote serializes one-dimensional finite NumPy embeddings as contiguous `float32` bytes with
dimension and dtype metadata. Pickle and JSON embedding storage are intentionally avoided.

## ADR-0014: Use Focused Local Parsers For Phase 3

- Status: Accepted
- Date: 2026-07-19

GroundNote uses `pypdf` for PDF text extraction and `python-docx` for DOCX text extraction. TXT
and Markdown are handled with the Python standard library. OCR and heavyweight document
frameworks are intentionally avoided for the MVP.

## ADR-0015: Keep Parsing Separate From Ingestion And Indexing

- Status: Accepted
- Date: 2026-07-19

Phase 3 validates, hashes, checks exact duplicates, and parses documents, but it does not create
chunks, generate embeddings, index documents, retrieve context, or call Foundry Local models. This
keeps parser safety and privacy concerns isolated before the ingestion pipeline is added.

## ADR-0016: Use Deterministic Hybrid Recursive Chunking

- Status: Accepted
- Date: 2026-07-19

GroundNote uses a custom deterministic chunker instead of a RAG framework. The chunker preserves
parsed section boundaries, PDF page numbers, DOCX and Markdown heading metadata, source order, and
safe warnings. It falls back from paragraphs to lightweight sentence splitting, whitespace
splitting, and hard character splitting only when needed. This keeps the MVP readable, local, and
independent from Foundry Local or embedding providers.

## ADR-0017: Persist Pre-Embedding Chunks In Phase 4

- Status: Accepted
- Date: 2026-07-19

Phase 4 persists document metadata and ordered chunk rows in one SQLite Unit of Work, ending with
`PENDING_EMBEDDING` status and null embedding fields. This matches the existing Phase 2 schema
direction and lets Phase 5 focus on embedding generation and indexing. Parser and chunking failures
roll back the transaction, repeated exact files do not create duplicates, and no document is marked
`INDEXED` before embeddings exist.

## ADR-0018: Store Normalized float32 Embeddings

- Status: Accepted
- Date: 2026-07-19

Phase 5 validates Foundry Local embedding output, converts vectors to `float32`, rejects NaN,
infinity, wrong dimensions, and zero vectors, then stores L2-normalized vectors as compact SQLite
BLOBs. Because stored vectors and query vectors use the same normalization policy, semantic
retrieval can use NumPy dot product as cosine similarity without adding FAISS or another vector
database.

## ADR-0019: Make Indexing Transactional And Retrieval INDEXED-Only

- Status: Accepted
- Date: 2026-07-19

Document indexing runs inside one SQLite Unit of Work and changes status from `PENDING_EMBEDDING`
to `INDEXING` to `INDEXED`. If embedding generation or persistence fails, the transaction rolls
back and the document remains non-searchable. Retrieval only loads chunks from `INDEXED` documents
whose embedding model and embedding version match the active settings.

## ADR-0020: Keep Phase 5 Retrieval Answer-Free

- Status: Accepted
- Date: 2026-07-19

Phase 5 returns ranked chunks, scores, and citation metadata only. It does not call a chat model,
build prompts, or generate natural-language answers. RAG generation remains explicitly deferred to
Phase 6.

## ADR-0021: Use The Local Foundry Daemon As An Embedding Load Fallback

- Status: Accepted
- Date: 2026-07-19

During the pre-Phase 6 audit, the installed Foundry Local preview SDK reported the embedding model
as cached but failed direct SDK loading with a missing model path for the selected CPU variant.
GroundNote keeps the SDK provider boundary, but the embedding provider may fall back to the
OpenAI-compatible Foundry Local daemon on `127.0.0.1` for the same local model variant. This is not
a cloud fallback, does not initialize chat generation, and unloads the embedding model after use.

## ADR-0022: Keep RAG Generation Single-Turn And Citation-Gated

- Status: Accepted
- Date: 2026-07-20

Phase 6 adds answer generation as a single-turn service instead of persistent conversation memory.
Grounded answers require retrieved context and at least one valid citation ID mapped from trusted
retrieval metadata. If no context exists, GroundNote returns a deterministic insufficient-evidence
message without loading the chat model. If a generated answer lacks citations, one repair attempt is
allowed before failing safely.

## ADR-0023: Use Loopback Foundry Daemon Fallback For Chat Preview Issues

- Status: Accepted
- Date: 2026-07-20

The chat provider first uses the Foundry Local SDK. If the installed preview runtime cannot load
the selected local model directly, the provider may load the same model variant through the local
Foundry daemon and call its OpenAI-compatible endpoint on loopback only. This is local inference,
does not permit arbitrary remote URLs, and does not add a cloud fallback.

## ADR-0024: Keep Local Model Inference Outside SQLite Write Transactions

- Status: Accepted
- Date: 2026-07-20

The Pre-Phase 7 UI readiness audit found that document indexing held a SQLite write transaction
open while the local embedding model loaded and generated vectors. That was safe for atomic
visibility but unnecessarily risky for a Streamlit UI, where reruns and status polling may happen
while indexing is in progress.

GroundNote now uses short transactions around database state changes and performs embedding model
loading/generation outside those write transactions. A document becomes `INDEXING` before model
work starts, remains non-searchable until all embeddings are saved and the document is marked
`INDEXED`, and becomes `FAILED` with a safe message if embedding generation fails. Retrieval still
loads only `INDEXED` documents with compatible embedding model/version metadata.

## ADR-0025: Cache Stateless UI Composition, Not Private Request Data

- Status: Accepted
- Date: 2026-07-20

Phase 7 uses one explicit application context to compose settings, database factories, Foundry
providers, ingestion, indexing, retrieval, RAG, and thin UI workflows. Streamlit caches this
stateless composition as a resource, but context construction does not load a model. SQLite
connections, transactions, uploaded bytes, extracted text, embeddings, prompts, and complete answer
caches are never stored in the cached resource.

Controlled `st.session_state` values contain operation flags, safe result models, selected source
IDs, and at most the latest single-turn question and answer. They do not form persistent chat
history and do not contain uploaded bytes, vectors, provider models, connections, or transactions.

## ADR-0026: Treat Explicit Model Evidence Refusals As Insufficient Evidence

- Status: Accepted
- Date: 2026-07-20

Manual Streamlit testing showed that a local model can retrieve a weakly related chunk, explicitly
state that the supplied documents lack enough evidence, and still append a required citation. A
citation alone must not turn that refusal into a grounded-success label.

GroundNote now recognizes a small conservative set of explicit English and Turkish
insufficient-evidence phrases after normal answer validation. Such output is replaced with the
existing deterministic language-matched insufficient-evidence response, all citations are removed,
and the UI displays an informational no-evidence state. Normal grounded answers remain unchanged.

## ADR-0027: Use Hybrid Local Retrieval For Stabilization

- Status: Accepted
- Date: 2026-07-20

Phase 7.1 removes the arbitrary pre-scoring SQL limit from semantic retrieval. All compatible
indexed vectors are eligible before NumPy scoring, which is acceptable for the MVP target of roughly
100-1500 chunks. SQLite FTS5 is added for local lexical matching over chunk content, section titles,
and filenames, then combined with vector ranking using deterministic boosts and tie-breaking.

This keeps retrieval local and understandable without adding an external search framework, vector
database, LangChain, LlamaIndex, or cloud service.

## ADR-0028: Route Simple Chat UX Messages Before RAG

- Status: Accepted
- Date: 2026-07-20

Greetings, thanks, and app-help questions are handled by a deterministic local router before
retrieval. These messages do not load the embedding model, do not load the chat model, do not search
documents, and do not produce citations. GroundNote remains a document assistant; document questions
continue through grounded RAG.

## ADR-0029: Keep Models Warm In Interactive Balanced Mode

- Status: Accepted
- Date: 2026-07-20

Phase 7 unloaded embedding and chat models after every operation, which made interactive use slow.
Phase 7.1 keeps application startup lightweight but allows models to remain loaded after first use
in Balanced mode. Fast mode uses the smaller fallback chat model with a lower output limit. Memory
saver mode and the explicit sidebar unload action release local models when the user prefers lower
memory usage over latency.

## ADR-0030: Use Streamlit-Safe Standard-Library File Logging

- Status: Accepted
- Date: 2026-07-20

Phase 7.1.1 removes the cached Structlog `PrintLogger` bound to Streamlit's temporary stdout. It uses
Structlog's standard-library integration with one idempotently configured UTF-8 local file handler.
The handler closes the file after every record so reruns do not retain stale console streams or
Windows file handles. Privacy processors still redact sensitive content. Narrow best-effort logging
helpers ensure a handler failure cannot mask the original application exception or block operation
cleanup.

## ADR-0031: Process Selected Uploads Sequentially With Session-Safe Identities

- Status: Accepted
- Date: 2026-07-20

GroundNote treats file selection as the trigger for automatic local processing. Stable opaque
upload identities and queued, active, completed, and failed session sets prevent ordinary Streamlit
reruns and settings changes from repeating work. Files run synchronously and sequentially without a
background worker, uploaded bytes are not retained in session state, duplicate detection happens
before model loading, and one file failure does not stop later files. Retry remains an inline action
on the affected failed document; deletion and full Knowledge Base management stay in Phase 8.

## ADR-0032: Prefer Deterministic Local Guardrails Before Model Work

- Status: Accepted
- Date: 2026-07-20

Phase 7.2 adds deterministic routing for empty, unclear, greeting, thanks, help, and no-ready
document states before retrieval or model calls. This keeps invalid inputs fast, prevents tracebacks
from short nonsense text, and avoids loading local models when no document answer is possible.

The RAG prompt is tightened to `grounded-rag-v2`, and generated answers are checked for repeated
words, repeated phrases, repeated citation markers, low-diversity tails, and excessive length.
GroundNote trims safe cited prefixes, retries once only when needed, and otherwise returns a
localized safe repetition error. Citation cleanup is local when possible and does not trigger an
extra full model generation.

The default RAG context and output budgets are reduced for local latency. The embedding service now
tracks provider loaded state, letting warm sessions reuse the embedding model for sequential upload
and retrieval bursts while Memory saver continues to unload models after each operation.

## ADR-0033: Keep Phase 7.2.1 Document Removal Minimal

- Status: Accepted
- Date: 2026-07-21

Phase 7.2.1 adds only a confirmed single-document remove action. It deletes the SQLite document row,
chunk rows, embeddings, and FTS rows through the existing Unit of Work, relying on local
transaction boundaries and parameterized repository methods. It does not delete the user's original
source file from disk and does not add Phase 8 bulk management, folders, re-index controls, or
advanced Knowledge Base screens.

## ADR-0034: Answer Document Inventory From Metadata

- Status: Accepted
- Date: 2026-07-21

Questions asking which documents are uploaded, indexed, grouped, or described are application
inventory requests rather than normal RAG questions. GroundNote answers them from safe indexed
document metadata and filename-derived topic hints. This avoids accidentally retrieving an old
unrelated older document and summarizing its content as if it were the document inventory.
The inventory path does not call the embedding model or chat model and does not fabricate page
citations.

## ADR-0035: Use Mode-Aware Local Model Cleanup

- Status: Accepted
- Date: 2026-07-21

Blindly unloading after every operation reduced RAM but made interactive use unnecessarily slow.
Phase 7.2.1 keeps mode-aware behavior: Fast keeps models warm longer, Balanced uses a short idle
TTL, and Memory saver unloads after each operation. The UI unloads chat models before indexing when
safe and avoids starting indexing and answer generation simultaneously in the normal Streamlit
flow. These controls reduce avoidable overlap but do not claim strict RAM or temperature caps.

## ADR-0036: Prefer Explicit Section Matches Before Broad RAG Context

- Status: Accepted
- Date: 2026-07-21

Phase 7.2.2 adds a conservative section-title filter between retrieval and RAG context assembly.
When a query explicitly names a retrieved section or item, GroundNote keeps matching-section chunks
and drops conflicting section chunks before building the prompt. Explicit comparison wording can
keep multiple named sections. If the title match is ambiguous, the original ranking is preserved
with a safe warning rather than guessing. This avoids mixing nearby document sections without
hardcoding document-specific facts.

## ADR-0037: Fail Fast When Named Entities Are Missing From Retrieved Evidence

- Status: Accepted
- Date: 2026-07-21

Some unrelated questions can retrieve superficially similar chunks because they share generic
technical terms. Phase 7.2.2 adds a named-entity coverage check after context selection. If the
question contains multiple strong named entities and the selected context does not contain them,
GroundNote returns localized insufficient evidence without loading the chat model or adding
citations. This preserves offline privacy, reduces latency, and avoids plausible but unsupported
answers.

## ADR-0038: Keep Knowledge Base Mutations Local, Transactional, and Sequential

- Status: Accepted
- Date: 2026-07-22

Phase 8 adds confirmed remove, clear-all, and per-document re-index controls through existing
SQLite Unit of Work boundaries. Clear all removes document records, chunks, embeddings, and FTS rows
inside one transaction, but deliberately never deletes the original uploaded source files. A
per-document re-index regenerates embeddings for the existing chunks and does not create duplicate
chunks or FTS entries. Re-index all is deferred because a synchronous bulk action would be expensive
and confusing without a background queue.

## ADR-0039: Keep Session Management In Memory Only

- Status: Accepted
- Date: 2026-07-22

New chat clears only the current `st.session_state` conversation messages. It preserves indexed
documents, user settings, and filters, is blocked during an active operation, and introduces no
persistent chat database or history-aware retrieval.

Phase 8.1 extends this session-only policy with a single privacy-safe flash notice for document
operation feedback. The notice contains localized display text and severity only, survives one
Streamlit rerun, and is consumed after rendering. Uploaded bytes, document content, raw paths,
prompts, vectors, and exceptions are never stored in the flash state.

## ADR-0040: Ship A Portable Source Archive Before A Native Installer

- Status: Accepted
- Date: 2026-07-22

GroundNote first adopted an allowlisted, deterministic source ZIP for the 0.9.0 packaging
foundation; the 1.0.0 release keeps it with uv-managed Python 3.11 and PowerShell setup/launcher
scripts. Foundry Local and its cached models remain external prerequisites.
This avoids fragile Streamlit/preview-SDK freezer hooks, unsigned executable antivirus false
positives, model bundling, and premature installer upgrade complexity. PyInstaller, Nuitka,
Briefcase, MSI, and MSIX remain documented future options after clean-machine, signing, licensing,
and upgrade/rollback validation.

## ADR-0041: Use Token-Scoped Launcher Metadata For Safe Shutdown

- Status: Accepted
- Date: 2026-07-22

The Windows launcher binds Streamlit to loopback and stores only its listener PID, launcher PID,
port, UTC start time, and a random session token in the platform-local GroundNote runtime folder.
The stop script verifies the token against the exact process command line and verifies the listener
owner before terminating anything. It never kills all Python processes and leaves Foundry Local
unchanged unless the user explicitly supplies `-StopFoundry`, because the local daemon may be shared
with another application.

## ADR-0042: Require Retrieved Evidence For Every Factual Document Answer

- Status: Accepted
- Date: 2026-07-22

GroundNote no longer contains topic-specific deterministic factual answers. A factual document
question must pass the generic retrieval overlap/entity checks and use the normal evidence prompt,
answer validation, and trusted citation map. Unrelated context produces the localized
insufficient-evidence response without citations. Deterministic routing remains only for greetings,
invalid input, app help, document inventory, explicit no-evidence behavior, and formatting-only
cleanup that does not introduce facts.

## ADR-0043: Prove Index Integrity Before Ready And Reconcile It At Bootstrap

- Status: Accepted
- Date: 2026-07-22

`INDEXED` means that a committed document has at least one chunk, a compatible finite float32
embedding for every chunk, matching document model metadata, and exactly one valid FTS row per
chunk. The final indexing transaction checks these counts before changing the status. Retrieval
queries repeat the complete-index predicate so incomplete records cannot become sources even before
the UI refreshes them.

At fresh bootstrap, persisted transient states are considered interrupted in the current
single-process architecture. Their partial embeddings and FTS rows are cleared and they become
retryable `FAILED` records. Committed pre-embedding chunks and the managed copy are preserved because
they form the only safe re-index input. This recovery is idempotent. The current schema cannot
preserve an old complete vector set while a replacement re-index is attempted, so a failed re-index
remains consistently non-searchable rather than exposing mixed versions.

## ADR-0044: Commit Database Deletion Before Validated Managed-Copy Cleanup

- Status: Accepted
- Date: 2026-07-22

Remove and clear-all commit their parameterized SQLite deletion first, then attempt to unlink only
the recorded GroundNote-managed direct child after canonical root containment, normal-file, and
reparse-point checks. Original selected files and unrelated files are never deletion targets. A
missing managed copy is an idempotent success. If validation, locking, or permissions prevent
cleanup, the database remains consistent and the UI shows a sanitized partial-cleanup warning.

This ordering avoids a filesystem deletion followed by a database rollback that would leave a
Ready record pointing to a missing managed copy. It can leave an orphaned managed copy after a
post-commit filesystem failure; automatic retry is deferred because the deleted row no longer
provides durable ownership metadata and guessing from filenames would weaken path safety.

## ADR-0045: Coordinate GroundNote-Owned Chat Models Through One Lifecycle

- Status: Accepted
- Date: 2026-07-22

Balanced and Fast providers share a process-local lifecycle coordinator. Activating a different
provider releases the current GroundNote-owned provider before loading the requested one; repeated
same-mode use reuses the active provider. Load/client/generation failures roll back the new owner,
and explicit shutdown is idempotent. Provider wrappers record whether GroundNote initiated a load,
so an already-loaded model that may belong to another application is not unloaded.

This establishes one active GroundNote chat model without broad daemon cleanup or assumptions about
other Foundry Local consumers. Direct WinML loads are not reliably reflected by the CLI daemon's
loaded-model count, so the lifecycle's active provider and ownership tests are authoritative.

## ADR-0046: Keep Indexing Synchronous and Block Chat During Indexing

- Status: Accepted
- Date: 2026-07-22

The representative 121-chunk workload spent 83.273 of 84.815 seconds in CPU-based embedding and
reported `562.9%` process CPU. The selected chat models are also CPU variants, and concurrent model
residency/inference was not demonstrated safe or useful on the target desktop. GroundNote therefore
keeps the existing single-process sequential operation guard and shows a context-specific localized
chat message while indexing.

A background worker, durable queue ownership, user cancellation, and simultaneous chat/indexing
would require lifecycle and recovery design outside this corrective phase. They remain deferred
rather than being approximated through Streamlit reruns.

## ADR-0047: Use Ordered Embedding Batches of 16 With Safe Stage Diagnostics

- Status: Accepted
- Date: 2026-07-22

The existing batch size of `16` already reduced a 121-chunk operation to eight provider calls with
stable ordering. The lifecycle/performance hardening keeps that conservative default and validates
configuration from `1`
through `64`; it does not maximize batch size based on a single machine. Later-batch failures commit
no partial vectors and unload the provider.

Indexing now records content-free stage durations, counts, model reuse, and best-effort process
CPU/RSS. These details are opt-in through technical details. Filenames, paths, document text,
prompts, questions, hashes, and vector values are excluded. The benchmark uses temporary storage
and cleans GroundNote-owned models afterward.

## ADR-0048: Own a Bounded Sequential Upload Queue in the Streamlit Session

- Status: Superseded by ADR-0049
- Date: 2026-07-22

The superseded design owned upload queue state in the current Streamlit session. A stable
submission identity
and opaque item identities prevent normal reruns from duplicating work. The queue retains one
bounded immutable byte buffer per waiting item because Streamlit's uploader object is not a durable
execution source; terminal outcomes release that buffer immediately. Queue metadata never contains
extracted text, prompts, vectors, raw exceptions, or paths.

Exactly one item may parse, embed, or write at a time, and chat remains blocked under one global
queue operation. The embedding provider may remain warm only across items in that queue, then all
GroundNote-owned providers are unloaded in final cleanup. Failed, invalid, and duplicate outcomes
are isolated so later items continue. Persisted failures retry through the existing re-index and
integrity contract; pre-persistence failures require the user to reselect the file.

The queue is intentionally not durable across a full browser session refresh or machine restart.
The database recovery contract remains authoritative for interrupted persisted records. A background
worker, parallel indexing, durable job service, and active-operation cancellation would introduce
new ownership and recovery semantics and remained outside that discarded queue design.

## ADR-0049: Prefer Single-file Upload and Process-local Indexing Ownership

- Status: Accepted
- Date: 2026-07-22

Manual product testing showed that retaining multiple browser uploads increased UI and session
complexity without reducing CPU-bound embedding time. GroundNote therefore accepts one file at a
time, retains no waiting document bytes, resets the uploader after every terminal outcome, and has
no background worker or persistent queue. The existing per-file size limit remains authoritative.

An `INDEXING` database row alone cannot distinguish genuinely active work from a process that died.
A database-scoped in-process registry now gives each synchronous indexing run an opaque ownership
token. Browser refreshes share that owner, so bootstrap does not recover live work as interrupted;
a true process restart clears the owner and preserves stale-state recovery.

Ready requires the complete final transaction and released ownership. While any indexing owner is
active, chat and document mutations are blocked and retrieval returns no document evidence, which
also preserves the no-overlap model lifecycle contract. This is deliberately local to the current
single-process Streamlit architecture and is not a durable job system.

## ADR-0050: Bound Untrusted Document Expansion Before Embedding

- Status: Accepted
- Date: 2026-07-22

A compressed upload-size limit cannot bound PDF work, DOCX expansion, extracted text, or generated
chunks. GroundNote therefore applies conservative validated defaults of 1,000 PDF pages, 5,000,000
extracted characters, 10,000 chunks, 200 MB DOCX declared expansion, 50 MB per DOCX member, a 100:1
compression ratio, and 2,000 DOCX members. Parsing stops when an incremental limit is crossed, and
the chunk limit is checked before persistence or embedding.

DOCX is treated as an untrusted ZIP archive. GroundNote validates central-directory metadata and
member paths, rejects encryption, special/link-like entries, duplicate names, unsafe XML entity
declarations, and excessive expansion, then reads only bounded `word/document.xml` and optional
`word/styles.xml` streams. It never extracts archive members to the filesystem. A pre-persistence
limit failure removes the temporary managed copy, loads no model, releases indexing ownership, and
cannot produce a searchable or Ready document.

## ADR-0051: Keep Release Setup Runtime-only and Make Launcher Startup Authoritative

- Status: Accepted
- Date: 2026-07-22

Portable-release setup uses `uv sync --no-dev`, and release-script `uv run` calls retain
`--no-dev`; developers continue to use the default `uv sync` development group. A present but
stopped or starting Foundry service is a doctor warning rather than a setup blocker because the
token-scoped launcher owns service startup. Missing CLI/runtime requirements, invalid
configuration, inaccessible storage, and occupied requested ports remain blocking. Missing cached
model aliases are actionable warnings and are never downloaded silently.

Launcher metadata is written atomically through a token-scoped temporary file after an HTTP health
check. Any startup or metadata failure terminates only processes whose command line carries that
invocation's token and removes partial metadata. Portable archives reject source-link/path boundary
violations, exclude all ZIP/checksum inputs, and emit a deterministic filename-only SHA-256
sidecar next to the reproducible ZIP.

## ADR-0052: Publish 1.0.0 as a Portable, Evidence-Backed Portfolio Release

- Status: Accepted
- Date: 2026-07-22

GroundNote 1.0.0 is the completed portfolio baseline. The public repository will explain actual
implemented behavior through a concise README, current architecture diagrams, original synthetic
demo material, measured performance, honest limitations, contribution/security guidance, and
privacy-safe screenshots. Temporary stabilization labels are consolidated into their owning public
phases; useful architectural decisions and historical changelog entries remain preserved.

The MIT license already selected by the repository remains in force. The portable deterministic
source ZIP remains the release format because Foundry Local, cached models, and uv are external
prerequisites and native installer signing/upgrade validation is incomplete. The 1.0.0 archive adds
public contribution/security files and demo examples to its allowlist while continuing to exclude
tests, databases, user documents, logs, models, caches, secrets, and generated ZIP/checksum inputs.

Publication uses one final commit containing the reviewed release-hardening work and the Phase 10
portfolio changes. A normal push to `main` is authorized only after the complete validation matrix
passes. Tags and GitHub Releases remain separate actions requiring later explicit authorization.
