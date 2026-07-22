# GroundNote Configuration

GroundNote uses a typed settings model in `groundnote.config.settings`. Settings are loaded from
safe defaults, an optional local `.env` file, and environment variables beginning with
`GROUNDNOTE_`.

## Environment Variables

Core settings:

- `GROUNDNOTE_ENV`: `development`, `test`, or `production`.
- `GROUNDNOTE_DEBUG`: `true` or `false`.
- `GROUNDNOTE_LOG_LEVEL`: any standard Python logging level such as `INFO` or `DEBUG`.

Path settings:

- `GROUNDNOTE_DATA_DIR`: optional base data directory.
- `GROUNDNOTE_DOCUMENT_DIRECTORY`: optional document storage directory.
- `GROUNDNOTE_DATABASE_DIRECTORY`: optional database directory.
- `GROUNDNOTE_DATABASE_PATH`: optional SQLite database path.
- `GROUNDNOTE_LOG_DIRECTORY`: optional log directory.

Model settings:

- `GROUNDNOTE_CHAT_MODEL`: default chat model.
- `GROUNDNOTE_EMBEDDING_MODEL`: embedding model.
- `GROUNDNOTE_EMBEDDING_BATCH_SIZE`: ordered local embedding batch size, from `1` through `64`;
  the conservative default is `16`.

Retrieval, upload, chunking, and generation settings:

- `GROUNDNOTE_TOP_K`
- `GROUNDNOTE_SIMILARITY_THRESHOLD`
- `GROUNDNOTE_MAXIMUM_UPLOAD_SIZE_MB`
- `GROUNDNOTE_MAXIMUM_PDF_PAGES`: default `1000`; valid range `1-10000`.
- `GROUNDNOTE_MAXIMUM_EXTRACTED_CHARACTERS`: default `5000000`; valid range
  `1-50000000`.
- `GROUNDNOTE_MAXIMUM_DOCUMENT_CHUNKS`: default `10000`; valid range `1-100000`.
- `GROUNDNOTE_DOCX_MAXIMUM_EXPANDED_SIZE_MB`: default `200`; valid range `1-1024`.
- `GROUNDNOTE_DOCX_MAXIMUM_COMPRESSION_RATIO`: default `100`; valid range `1-1000`.
- `GROUNDNOTE_DOCX_MAXIMUM_MEMBER_SIZE_MB`: default `50`; valid range `1-512`.
- `GROUNDNOTE_DOCX_MAXIMUM_MEMBERS`: default `2000`; valid range `1-10000`.
- `GROUNDNOTE_CHUNK_TARGET_CHARACTERS`
- `GROUNDNOTE_CHUNK_MAXIMUM_CHARACTERS`
- `GROUNDNOTE_CHUNK_OVERLAP_CHARACTERS`
- `GROUNDNOTE_CHUNK_MINIMUM_CHARACTERS`
- `GROUNDNOTE_CHUNKING_VERSION`
- `GROUNDNOTE_RAG_MAX_OUTPUT_TOKENS`: default `320`.

The document limits stop untrusted expansion and chunk generation before local embedding. Raising
them increases memory, CPU, and indexing-time risk; `.env.example` keeps the conservative release
defaults.

## Defaults

When no path is provided, GroundNote uses `platformdirs` to select a normal per-user local data
directory. The application then derives:

- document directory: `<data>/documents`
- database directory: `<data>/database`
- database path: `<data>/database/groundnote.sqlite3`
- log directory: `<data>/logs`

Importing settings does not create directories. Directories are created only by
`Settings.initialize_directories()` or the application bootstrap flow.

## Development Paths

For local development, use `.env` to point paths at a project-local directory if desired:

```powershell
GROUNDNOTE_DATA_DIR=.local-data
GROUNDNOTE_DATABASE_PATH=.local-data/database/groundnote.sqlite3
```

Do not commit `.env` or local generated data.

## No API Key Requirement

GroundNote does not require cloud AI API keys. The selected model aliases are for Microsoft
Foundry Local.

## Safe Database Overrides

`GROUNDNOTE_DATABASE_PATH` must end with `.db`, `.sqlite`, or `.sqlite3`. Parent directories are
created only during explicit bootstrap, not during settings import.
