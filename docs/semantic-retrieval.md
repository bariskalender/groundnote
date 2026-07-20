# Semantic Retrieval

Phase 5 adds local semantic retrieval over indexed chunk embeddings. It returns ranked source
chunks and citation metadata. Phase 6 uses these results for grounded RAG answers.

## Query Embedding

Queries are trimmed and embedded with the same configured Foundry Local embedding model used for
indexed chunks. Empty queries are rejected. Turkish, English, and Unicode text are preserved; the
query is not lowercased, translated, or sent to a chat model.

## Candidate Loading

Retrieval loads only chunk embeddings from `INDEXED` documents and only when the stored embedding
model and embedding version match the active configuration. `PENDING_EMBEDDING`, `INDEXING`,
`FAILED`, and incompatible documents are excluded.

## Similarity

GroundNote stores normalized `float32` vectors. Retrieval normalizes the query vector through the
same policy and uses NumPy dot product as cosine similarity. Scores range from `-1.0` to `1.0`.
Higher scores are ranked first.

Synthetic vector tests prove the math implementation, not universal semantic quality.

## Limits And Filters

MVP defaults:

- `top_k`: `5`.
- candidate limit: `50`.
- minimum score: `0.20`.

`top_k` is bounded to 20 and the candidate limit is bounded to 500. Filters currently support:

- document IDs;
- source file type;
- page number;
- minimum score.

No complex query language is implemented.

## Stable Ordering

Results use deterministic ordering:

1. score descending;
2. document ID;
3. chunk index;
4. chunk ID.

## Result Metadata

Each retrieval result includes:

- document ID;
- chunk ID;
- chunk index;
- chunk content;
- score;
- source filename;
- source file type;
- page number when available;
- section title when available;
- source ordering metadata;
- safe chunk metadata.

This metadata is used by the Phase 6 RAG service for citations and context assembly.

## Privacy

Retrieval logs safe metadata such as query character count, candidate count, returned count, model,
limits, and duration. It does not log full query text, chunk content, raw vectors, embedding BLOBs,
or absolute local file paths.

## Current Limitations

- Semantic retrieval does not guarantee perfect relevance.
- Answer generation is implemented in the separate Phase 6 RAG service, not in retrieval.
- No Streamlit search or chat UI is implemented yet.
