# Model Lifecycle and Indexing Performance

GroundNote keeps local model ownership explicit and conservative. This document records the current
1.0.0 behavior and actual measurements; it does not promise equivalent performance on different
hardware, documents, Foundry versions, or model variants.

## Ownership Rules

- Application startup, status rendering, duplicate detection, and deterministic chat routes load no
  model.
- Balanced and Fast chat providers share one process-local lifecycle coordinator.
- Switching modes unloads the prior GroundNote-owned chat provider before loading the next one.
- Repeated same-mode questions may reuse the active provider under the selected cleanup policy.
- A provider that was already loaded and may belong to another local application is not unloaded.
- Embedding resources are released before the chat generation handoff.
- Provider load, client, generation, indexing, retrieval, and shutdown failures perform
  ownership-aware cleanup.
- Manual unload and process shutdown are idempotent.

Foundry CLI loaded-model counts may not reflect every direct WinML load, so GroundNote also tracks
the provider it owns. It never uses broad model or process cleanup to approximate ownership.

## Indexing Contract

Indexing remains synchronous and sequential. A user selects one file; GroundNote validates, parses,
chunks, embeds in ordered batches, verifies storage, and reports a terminal result before another
file is accepted. Chat and document mutations are blocked while an indexing owner is active.

The default embedding batch size is `16`, validated from `1` through `64`. The batch size was not
increased merely to optimize one machine. Later-batch and persistence failures leave no usable
partial vectors or FTS rows.

The UI exposes real stage boundaries and chunk progress. Optional technical details contain only
content-free durations, counts, model reuse, and best-effort process CPU/RSS. They exclude
filenames, paths, text, hashes, questions, prompts, vectors, and raw errors.

## Representative Measurement

The isolated benchmark used an original generated plain-text fixture and the configured
`qwen3-embedding-0.6b` model through the available CPU execution provider.

| Metric | Measured value |
| --- | ---: |
| Input bytes | 76,601 |
| Extracted characters | 76,360 |
| Chunks | 121 |
| Embedding batches | 8 |
| Model load | 1.375 s |
| Embedding generation | 82.300 s |
| Total indexing | 83.833 s |
| Observed peak process RSS | 896.441 MB |
| Loaded model count after cleanup | 0 |

Hash reuse avoided a second uploaded-file read and filesystem hash. The same content was parsed and
chunked once. CPU embedding accounted for nearly all elapsed time and is the main observed indexing
bottleneck.

Earlier lightweight model-candidate measurements are preserved in
[`model-benchmark.md`](model-benchmark.md). They use a different tiny workload and should not be
compared directly with the 121-chunk indexing run.

## Why Chat Is Disabled During Indexing

The measured workload spent 82.300 of 83.833 seconds in CPU embedding, and the selected chat model
variants also used CPU execution providers. Safe, useful simultaneous inference was not established
on the target machine. GroundNote therefore avoids keeping embedding and chat inference active at
the same time.

A cancellable background worker would require durable ownership, restart recovery, progress
persistence, queue limits, model coordination, and an explicit user cancellation contract. Those
features are future work rather than hidden behavior in Streamlit reruns.

## Running the Benchmark

```powershell
uv run python scripts/benchmark_indexing.py
```

The script uses an isolated temporary database and managed-document directory, reports sanitized
JSON metrics, and cleans GroundNote-owned models and temporary files. An explicit fixture path is
optional; never use a private document in published benchmark output.

## Limits of the Evidence

- Measurements came from one Windows 11 development machine.
- The installed Foundry catalog selected CPU variants despite an available NVIDIA GPU.
- No GPU/NPU acceleration claim is made.
- One synthetic workload does not represent every PDF/DOCX parser or document structure.
- Warm cache state, antivirus, power policy, and Foundry preview changes can alter results.
- There was no stress, 7B+, parallel-model, or long-generation test.
