# Phase 9.1B Model Lifecycle and Indexing Performance

Phase 9.1B measured the existing synchronous indexing path, tightened local model ownership, and
added privacy-safe stage diagnostics. It did not add a background worker, concurrent inference, or
new model aliases.

## Model Lifecycle

Balanced (`phi-3.5-mini`) and Fast (`qwen2.5-0.5b`) share one application lifecycle coordinator.
Activating one GroundNote-owned chat provider unloads the previously active provider before loading
the next. Repeated use of the same provider reuses it. Generation, client construction, direct SDK,
and daemon-fallback failures roll back only resources loaded by GroundNote. A model found already
loaded is treated as externally owned and is not unloaded.

Embedding cleanup covers model-load, first/later batch, vector persistence, FTS, integrity, query
embedding, interruption, and explicit application shutdown paths. The retrieval service releases
the embedding model before chat generation, preventing embedding/chat overlap in the normal RAG
flow.

## Indexing Flow

The operation reports these measured stages: upload save, validation, hashing, duplicate check,
parsing, chunking, chunk save, embedding model load, embedding, vector save, FTS synchronization,
integrity verification, and finalization. Normal UI output stays concise. Timings, counters, model
reuse, process RSS, and process CPU are visible only when technical details are enabled.

The uploader reads and hashes selected bytes once. Its transient selection object carries the bytes
only for the current rerun and stores neither them nor the digest in Streamlit session state. The
verified digest is reused by ingestion, avoiding a second file hash. Parsing and chunking each occur
once. Duplicate detection remains before embedding. Completed metadata is read from SQLite, and
reruns do not create a second indexing job.

Embedding remains sequential and ordered with a configurable batch size. The default is `16`; the
validated range is `1` through `64`. A 121-chunk fixture therefore uses eight provider calls. A
later-batch failure persists no partial vectors and leaves the document retryable.

## Measured Results

Measurements are local observations, not universal performance claims. They were taken on Windows
11 (`10.0.22621`), Ryzen 7 7840HS, 31.3 GB detected RAM, and an RTX 4050 Laptop GPU. Foundry Local
selected `CPUExecutionProvider` for all three candidate models, so embedding was CPU-bound. Foundry
CLI was `0.10.2`, Windows SDK was `1.2.3`, and Python was `3.11.15`.

| Metric | Before instrumentation | Phase 9.1B isolated benchmark |
| --- | ---: | ---: |
| Fixture size | 78,022 bytes | 76,601 bytes |
| Extracted characters | about 78,022 | 76,360 |
| Pages | Not applicable (Markdown) | Not applicable (Markdown) |
| Chunks | 120 | 121 |
| Batch size / calls | 16 / 8 | 16 / 8 |
| Model load | 4.917 s | 1.397 s |
| Embedding | 80.492 s | 83.273 s |
| Total | 85.633 s | 84.815 s |
| Peak process RSS | about 1,577.5 MB | 894.9 MB |
| Loaded models before / after cleanup | 0 / 0 | 0 / 0 |

The representative fixtures are similar in size and structure but not byte-identical. The roughly
0.8-second total difference must therefore be treated as essentially flat, not as a throughput
claim. The lower observed process RSS is encouraging but is also sensitive to process warm state.
The reliable finding is that embedding consumes more than 98% of total time on the current CPU
runtime; parsing, chunking, SQLite writes, FTS, and integrity checks are small by comparison.

The deterministic fake-provider run on the same Phase 9.1B fixture completed in about 82 ms with
about 141.2 MB peak process RSS. This isolates local model inference as the dominant cost rather
than Streamlit reruns, parsing, or SQLite.

## Concurrency Decision

Chat remains unavailable while synchronous indexing is active. The measured embedding operation
used up to roughly 5.6 logical CPU cores (`562.9%` process CPU in psutil convention), while the chat
models are also CPU variants sized at approximately 822 MB and 2,590 MB. Running both would add CPU
contention and model-memory pressure, and Streamlit's current single-process rerun model provides no
durable job ownership or cancellation contract. A background queue is therefore deferred. The UI
uses distinct localized indexing and chat-busy messages and real chunk counters instead of fake
percentages.

## Reproducing Safely

The quick fake-provider profile is:

```powershell
uv run python scripts/benchmark_indexing.py --sections 120 --batch-size 16
```

After verifying Foundry and cached models, the real local profile is:

```powershell
uv run python scripts/benchmark_indexing.py --sections 120 --batch-size 16 --real-foundry
```

An explicit supported file may be supplied with `--file`, but its path, filename, text, hash, and
vectors are not emitted. Every run uses a temporary database and managed document directory, then
unloads GroundNote-owned models and removes the temporary tree.

## Limitations

- Foundry's catalog reported zero daemon-loaded models during direct WinML inference; the shared
  lifecycle's active alias and provider-level tests are the authoritative ownership signal.
- The current catalog variants are CPU-only despite an available NVIDIA GPU. Phase 9.1B does not
  change model/runtime selection merely to improve benchmark numbers.
- Cancellation is best-effort process-interruption cleanup, not a user-facing cancel button.
- Multi-file background queues and simultaneous chat/indexing are intentionally not implemented.
