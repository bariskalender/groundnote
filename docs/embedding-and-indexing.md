# Embedding And Indexing

Phase 5 adds local embedding generation and indexing for chunks that were prepared by Phase 4.
GroundNote uses Microsoft Foundry Local with the configured embedding model
`qwen3-embedding-0.6b`.

## Configuration

- Model: `qwen3-embedding-0.6b`.
- Dimension: `1024`.
- Dtype: `float32`.
- Batch size: `16`.
- Version: `foundry-qwen3-embedding-v1`.
- Normalization policy: vectors are validated and L2-normalized before persistence.

These are MVP defaults, not universal constants.

## Provider Boundary

Foundry SDK details remain inside the AI provider layer. The indexing workflow calls a provider
through `EmbeddingService`, which validates vector count, dimension, dtype, finite values, and
positive norm. The chat model is not loaded or called by Phase 5.

If direct SDK model loading fails because of a Foundry Local preview runtime/cache mismatch, the
embedding provider may use the OpenAI-compatible Foundry Local daemon on `127.0.0.1` for the same
local embedding model variant. This remains local-only and does not fall back to a cloud API.

## Batching

Chunks are embedded sequentially in configured batches. Input order is preserved and the final
partial batch is supported. Empty inputs are rejected. No concurrent model calls are made.

## Serialization And SQLite Storage

Embeddings are serialized as compact `float32` bytes by the existing storage codec. Pickle and JSON
numeric arrays are not used. SQLite stores embedding BLOBs on chunk rows together with:

- embedding dimension;
- embedding dtype;
- embedding model;
- embedding version;
- embedded timestamp.

The document row stores indexing status, indexed timestamp, embedding model, embedding dimension,
and embedding version.

## Status Transitions

Normal indexing starts only from `PENDING_EMBEDDING`.

```text
PENDING_EMBEDDING -> INDEXING -> INDEXED
```

`INDEXED` means every chunk for that document has a valid embedding. Already indexed documents are
rejected unless `force_reindex=True` is requested.

## Transaction And Failure Behavior

Document status changes and chunk embedding writes occur inside one Unit of Work transaction. If
embedding generation or persistence fails, the transaction rolls back and the document remains
non-searchable. Retrieval only considers documents with `INDEXED` status.

Force re-indexing clears old embeddings transactionally, regenerates all embeddings, preserves
document and chunk identities, and does not duplicate chunks.

## Model Compatibility

Retrieval filters candidates by the active embedding model and embedding version. GroundNote does
not compare vectors from incompatible models or versions.

## Current Limitations

- No natural-language answer generation is implemented.
- No background indexing jobs are implemented.
- No external vector database or SQLite vector extension is used.
- First-time model downloads require internet; cached inference runs locally.
