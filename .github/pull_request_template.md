## Summary

Describe the bounded change and the user-facing reason.

## Validation

- [ ] `uv run ruff check .`
- [ ] `uv run ruff format --check .`
- [ ] `uv run mypy src`
- [ ] `uv run pytest -m "not foundry"`
- [ ] Relevant documentation and real Foundry/manual checks are recorded.

## Privacy and release safety

- [ ] No private/copyrighted documents, databases, logs, prompts, vectors, secrets, models, caches,
      personal paths, or generated release artifacts are included.
- [ ] Local-only inference, safe logging, provider isolation, and document-as-untrusted-data
      boundaries remain intact.
- [ ] Behavior changes include focused fake-provider regression coverage.
