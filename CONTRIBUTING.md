# Contributing to GroundNote

Thank you for helping improve GroundNote. Contributions should preserve its local privacy boundary,
readable architecture, and conservative desktop resource use.

## Development Setup

GroundNote targets Python 3.11 and uses uv:

```powershell
uv sync
uv run python -m groundnote --version
uv run streamlit run src/groundnote/app.py
```

Microsoft Foundry Local is required only for explicit real-model checks. Normal unit tests use fake
providers and must not download a model.

## Quality Checks

Run these before submitting a pull request:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest -m "not foundry"
uv run pytest --cov=groundnote --cov-report=term-missing
```

When changing setup, launcher, model integration, or packaging, also run the relevant scripts and
document the actual environment and results. Never claim a real Foundry path works without executing
it.

## Coding Style

- Use English source code, identifiers, comments, documentation, and UI keys.
- Prefer small functions, explicit types, plain data models, and existing service boundaries.
- Use parameterized SQL and Unit of Work transactions for data changes.
- Keep Foundry Local SDK details behind provider interfaces.
- Treat document text as untrusted data, never as instructions.
- Do not add cloud fallbacks, telemetry, analytics, or remote logging.
- Do not broaden model concurrency or background processing without a complete ownership and
  recovery design.

## Fixtures and Screenshots

- Use original synthetic material or clearly redistribution-safe project-owned fixtures.
- Never commit course notes, uploaded user documents, local databases, logs, prompts, embeddings,
  answers, model files, `.env`, credentials, or runtime metadata.
- Screenshots must contain no personal paths, usernames, accounts, bookmarks, tokens, private
  filenames, or private document content.
- Do not copy copyrighted teaching material into a fixture, example, issue, or pull request.
- Keep real-model smoke data in isolated temporary directories and remove it afterward.

## Pull Requests

A pull request should:

1. describe the user-facing problem and the bounded change;
2. link a relevant issue when one exists;
3. list commands actually executed and their results;
4. disclose any test that was skipped and why;
5. update documentation for behavior, configuration, privacy, or limitations changes; and
6. avoid unrelated formatting, generated artifacts, or history rewrites.

Keep changes small enough to review. New functionality should include fake-provider tests; real
Foundry tests must remain explicitly marked or manual so routine CI/development does not download
models.
