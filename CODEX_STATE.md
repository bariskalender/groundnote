# Codex State

## Current Phase

Phase 1: Environment verification and Foundry Local discovery.

## Completed Tasks

### Phase 0

- Created the src-layout repository structure.
- Added governance documents, dependency configuration, quality tooling, and a minimal
  Streamlit application shell.
- Added a smoke test that imports the package.
- Verified Ruff, mypy, pytest, and a short Streamlit startup smoke test.

### Phase 1

- Installed Microsoft Foundry Local CLI with `winget install Microsoft.FoundryLocal`.
- Verified Foundry Local CLI version `0.10.2`.
- Verified Foundry daemon status through `foundry server status`.
- Installed `foundry-local-sdk-winml` `1.2.3` and `openai` `2.46.0`.
- Confirmed the SDK initializes and lists 46 model aliases.
- Confirmed candidate aliases exist: `phi-3.5-mini`, `qwen2.5-0.5b`, and
  `qwen3-embedding-0.6b`.
- Added provider-neutral AI interfaces and data models.
- Added Foundry manager, chat provider, embedding provider, and fake providers.
- Added unit tests for fake providers.
- Added `scripts/check_foundry.py` and `scripts/benchmark_models.py`.
- Added `docs/foundry-local-setup.md` and actual benchmark results in
  `docs/model-benchmark.md`.
- Updated `README.md`, `.env.example`, `ROADMAP.md`, and `DECISIONS.md`.

## Commands Run In Phase 1

- `winget install Microsoft.FoundryLocal --accept-source-agreements --accept-package-agreements`
- `foundry --version`
- `foundry status`
- `foundry server status`
- `foundry model list`
- `foundry model list --limit 60`
- `nvidia-smi --query-gpu=name,driver_version,memory.total,memory.free --format=csv,noheader`
- `uv sync`
- `uv run python scripts/check_foundry.py`
- `uv run python scripts/benchmark_models.py`
- `uv run ruff check .`
- `uv run mypy src`
- `uv run pytest -m "not foundry"`

## Test Status

- `uv sync`: Passed.
- `uv run python scripts/check_foundry.py`: Passed.
- `uv run python scripts/benchmark_models.py`: Passed.
- `uv run ruff check .`: Passed.
- `uv run mypy src`: Passed.
- `uv run pytest -m "not foundry"`: Passed, 3 tests passed.

## Model Benchmark Status

- `phi-3.5-mini`: Loaded, generated `4`, and unloaded successfully.
- `qwen2.5-0.5b`: Loaded, generated `4`, and unloaded successfully.
- `qwen3-embedding-0.6b`: Loaded, produced finite float32 embeddings, passed cosine sanity
  check, and unloaded successfully.
- Final cached benchmark measurements are recorded in `docs/model-benchmark.md`.
- Final model decision:
  - Default chat model: `phi-3.5-mini`
  - Low-resource fallback chat model: `qwen2.5-0.5b`
  - Embedding model: `qwen3-embedding-0.6b`

## Known Issues

- `uv` is installed but is not on PATH for this shell, so commands were run through the installed
  executable.
- `python` and `py` are not on PATH; the project uses managed Python 3.11.15 through `uv`.
- The installed Foundry Local CLI uses `foundry server status`; Microsoft Learn currently also
  documents `foundry service status`, which is not recognized by CLI `0.10.2`.
- CLI catalog lists default hardware target as GPU for the candidate aliases, but the Phase 1
  SDK benchmark with project-local SDK configuration resolved and ran CPU variants. GPU hardware
  is visible, but no GPU variant was forced in Phase 1.
- First benchmark run downloaded models and required internet. The final benchmark used cached
  models and should be reproducible offline as long as the cache remains present.
- `pytest` passed but emitted a non-failing cache warning because `.pytest_cache` could not be
  written in this Windows workspace.

## Environment Facts

- OS: Microsoft Windows 11 Pro, version 10.0.22621, 64-bit.
- CPU: AMD Ryzen 7 7840HS, 16 logical cores.
- GPU detected: NVIDIA GeForce RTX 4050 Laptop GPU.
- NVIDIA driver: 610.74.
- NVIDIA VRAM reported by `nvidia-smi`: 6141 MiB total, about 5818 MiB free during check.
- Foundry Local CLI: `0.10.2`.
- Foundry Local SDK: `foundry-local-sdk-winml` `1.2.3`.
- OpenAI-compatible client dependency: `openai` `2.46.0`.
- Managed Python: 3.11.15.
- `uv`: 0.11.29.

## Next Phase

Phase 2: Configuration, logging, and application settings.
