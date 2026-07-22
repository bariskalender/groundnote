# GroundNote Release Checklist

## Version and source

- [ ] Update `[project].version` in `pyproject.toml`.
- [ ] Confirm `python -m groundnote --version` matches the release.
- [ ] Add the release section to `CHANGELOG.md`.
- [ ] Confirm ROADMAP, PROJECT_STATE, README, and release documentation are current.
- [ ] Confirm screenshots contain only the original safe demo content and no personal UI chrome.
- [ ] Confirm the working tree contains only intended release changes.

## Quality gates

- [ ] Run `uv sync`.
- [ ] Run `uv run ruff check .` and `uv run ruff format --check .`.
- [ ] Run `uv run mypy src`.
- [ ] Run `uv run pytest -m "not foundry"` and coverage.
- [ ] Parse every PowerShell script with the PowerShell language parser.
- [ ] Run the doctor without starting Streamlit.

## Windows workflow

- [ ] Run setup twice against isolated data and confirm existing data remains.
- [ ] Confirm setup installs runtime dependencies with `uv sync --no-dev` and succeeds with a
  warning when Foundry Local is installed but stopped.
- [ ] Start with `scripts/start_groundnote.ps1 -Background -NoBrowser`.
- [ ] Run the launcher again and confirm it reports the existing instance.
- [ ] Confirm the URL is loopback-only and the Knowledge Base is preserved.
- [ ] Stop with `scripts/stop_groundnote.ps1` and confirm no listener remains.
- [ ] Simulate a runtime-metadata write failure and confirm only the token-owned launch is stopped,
  partial metadata is removed, and the selected port is free.
- [ ] Confirm no unrelated Python or Foundry process was terminated.

## Models and product smoke

- [ ] Confirm required model aliases are cached without downloading them.
- [ ] Run fake-provider UI smoke and real Foundry smoke only when safe.
- [ ] Ask one grounded question using a non-private release fixture.
- [ ] Confirm loaded model count returns to zero when the lifecycle expects it.
- [ ] Never modify or delete a user's real documents during release validation.

## Archive

- [ ] Run `scripts/build_release_archive.ps1`.
- [ ] Verify `groundnote-<version>.zip.sha256` against the ZIP and confirm it contains no absolute
  path.
- [ ] Build twice from identical input and confirm the ZIP SHA-256 values match.
- [ ] Inspect every ZIP member without extracting into a user data folder.
- [ ] Confirm required scripts, source, lockfile, configuration example, docs, and license exist.
- [ ] Confirm CONTRIBUTING, SECURITY, and the original demo examples exist.
- [ ] Confirm `.env`, databases, documents, logs, caches, models, vectors, tests, and Git metadata do
  not exist in the ZIP.
- [ ] Confirm no current/prior ZIP or checksum is a ZIP member and extract under a path containing
  spaces.
- [ ] Run isolated extracted-release setup, doctor, start, HTTP health, and scoped stop from a path
      containing spaces.
- [ ] Record separate clean Windows account/VM testing when available; do not imply it was run.

## Publication boundary

- [ ] Create/push tags or releases only after explicit authorization.
- [ ] Do not upload user data, local logs, model files, or caches.
- [ ] Do not publish a release from a dirty or unvalidated tree.

## Version bump instructions

1. Change only `[project].version` in `pyproject.toml`.
2. Run `uv sync` so editable metadata and the lockfile agree.
3. Add a dated changelog entry.
4. Run the full checklist and rebuild the archive.

The package reads its runtime version through `importlib.metadata`; no second source-code version
constant should be edited.
