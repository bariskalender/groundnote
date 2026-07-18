# GroundNote Model Benchmark

Created at: `2026-07-18T19:28:25.654617+00:00`

## Safety Notes

- Model download requires internet on first run.
- Cached inference should work offline after local model files are available.
- No cloud API was used.
- Models were loaded sequentially; no stress test was run.
- The CLI catalog listed GPU as the default target, but this SDK benchmark ran CPU variants with
  project-local Foundry SDK configuration.

## Chat Candidates

| Alias | Cached before | Download s | Load s | Response s | RSS before MB | RSS after MB | Passed | Error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| phi-3.5-mini | True |  | 5.85 | 0.505 | 123.43 | 3358.59 | True |  |
| qwen2.5-0.5b | True |  | 2.643 | 0.135 | 136.4 | 620.47 | True |  |

## Embedding Candidate

| Alias | Cached before | Download s | Load s | Batch s | Dimension | Same cosine | Different cosine | Passed | Error |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| qwen3-embedding-0.6b | True |  | 2.433 | 1.583 | 1024 | 1.0 | 0.189289 | True |  |

## Model Decision

- Default chat model: `phi-3.5-mini`
- Low-resource fallback chat model: `qwen2.5-0.5b`
- Embedding model: `qwen3-embedding-0.6b`
