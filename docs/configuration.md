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
- `GROUNDNOTE_CHAT_MODEL_FALLBACK`: low-resource fallback chat model.
- `GROUNDNOTE_EMBEDDING_MODEL`: embedding model.
- `GROUNDNOTE_EMBEDDING_BATCH_SIZE`: ordered local embedding batch size, from `1` through `64`;
  the conservative default is `16`.

Retrieval, upload, chunking, and generation settings:

- `GROUNDNOTE_TOP_K`
- `GROUNDNOTE_SIMILARITY_THRESHOLD`
- `GROUNDNOTE_MAX_UPLOAD_MB`
- `GROUNDNOTE_MAX_UPLOAD_FILES`: maximum files retained in the in-session queue; default `10`,
  valid range `1` through `25`.
- `GROUNDNOTE_MAX_UPLOAD_TOTAL_MB`: combined waiting-buffer limit; default `100`, valid range `1`
  through `500`, and never lower than the per-file limit.
- `GROUNDNOTE_CHUNK_TARGET_CHARS`
- `GROUNDNOTE_CHUNK_MAX_CHARS`
- `GROUNDNOTE_CHUNK_OVERLAP_CHARS`
- `GROUNDNOTE_MIN_CHUNK_CHARS`
- `GROUNDNOTE_CHUNKING_VERSION`
- `GROUNDNOTE_MAXIMUM_OUTPUT_TOKENS`
- `GROUNDNOTE_TEMPERATURE`

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
