# Pre-Embedding Ingestion

Phase 4 connects Phase 3 validation and parsing to deterministic chunking and transaction-safe
SQLite persistence. It stops before embedding generation.

## Processing Flow

The `PreEmbeddingIngestionService` performs:

1. Validate the local file using the Phase 3 safety checks.
2. Calculate the SHA-256 digest from original file bytes.
3. Check for an exact duplicate before parsing and chunking.
4. Parse PDF, DOCX, TXT, or Markdown into `ParsedDocument` and `ParsedSection` values.
5. Chunk the parsed document with `HybridRecursiveChunker`.
6. Create an `IngestionPlan`.
7. Persist document metadata and pre-embedding chunks in one SQLite Unit of Work.

## Duplicate Behavior

Exact duplicates are detected by SHA-256 before expensive parsing and chunking. A repeated exact
file raises the safe duplicate document error and does not create a new document or chunk rows.
Automatic version replacement is not implemented in Phase 4.

## Status Transitions

The preferred logical flow is:

```text
PENDING -> PARSING -> PARSED -> PENDING_EMBEDDING
```

Phase 4 persists the successful final pre-embedding state as `PENDING_EMBEDDING`. It never marks a
document as `INDEXED`.

## Persistence

On success, GroundNote stores:

- one document metadata record;
- ordered chunk rows;
- page numbers where available;
- section titles where available;
- character counts and approximate token estimates;
- source order metadata;
- chunking version and safe JSON metadata.

Before Phase 5, these fields remain null:

- embedding BLOB;
- embedding dimension;
- embedding dtype;
- document embedding model;
- document indexed timestamp.

## Transaction Behavior

Document metadata and chunks are written in a single transaction after parsing and chunking
succeed. Parser failures, chunking failures, duplicate detection, or storage errors roll back the
transaction so partial persistent state is not exposed.

## Current Limitations

- No embeddings are generated.
- No semantic retrieval path is implemented.
- No RAG answer generation is implemented.
- The final Streamlit upload and chat workflow is not implemented.
- Foundry Local is not initialized or called by Phase 4 ingestion.
