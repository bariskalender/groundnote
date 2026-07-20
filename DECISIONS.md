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
