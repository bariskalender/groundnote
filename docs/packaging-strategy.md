# Packaging Strategy

## Decision

GroundNote `1.0.0` uses a versioned portable source archive with PowerShell setup and launcher
scripts. This is the lowest-risk option while Foundry Local remains preview software and models are
large, hardware-dependent external assets.

## Options considered

| Direction | Benefits | Main risks | Phase 9 decision |
| --- | --- | --- | --- |
| Repository checkout + scripts | Transparent and easy to debug | Requires Git or source download | Supported for development |
| Portable source ZIP + scripts | Small, inspectable, reproducible | First setup needs uv and Foundry | Recommended |
| PyInstaller | Can bundle Python runtime | Streamlit/SDK hooks, size, antivirus false positives | Deferred |
| Nuitka | Native compilation opportunities | Long builds and toolchain complexity | Deferred |
| Briefcase | Desktop packaging conventions | Streamlit browser architecture mismatch | Deferred |
| MSI tooling | Familiar enterprise installation | Signing, upgrades, scope complexity | Deferred |
| MSIX/Windows Store | Sandboxing and update channel | Store policy and runtime integration | Future option |

## Evaluation

- **Foundry Local:** remains separately installed and versioned; its models are never copied.
- **Model size:** 0.5-3 GB candidates make bundling inappropriate.
- **Streamlit:** source launch avoids frozen-runtime hooks.
- **Python:** uv installs the locked Python 3.11 environment reproducibly.
- **Antivirus:** a source ZIP avoids unsigned self-extracting executable heuristics.
- **Updates:** application source can be replaced while platform-local user data stays separate.
- **Offline use:** dependencies and models need initial preparation; cached inference stays local.
- **Repository size:** the archive excludes Git history, tests, caches, models, and data.
- **Licensing:** model and dependency licenses remain part of their own install/download workflows.

## Archive contract

`scripts/build_release_archive.ps1` creates `dist/groundnote-<version>.zip` with sorted entries and
fixed timestamps, plus `groundnote-<version>.zip.sha256` containing the lowercase SHA-256 and ZIP
filename. Included content is limited to runtime source, locked metadata, safe configuration
example, Streamlit configuration, user scripts, documentation, original demo examples,
contribution/security guidance, changelog, and license.

The builder rejects invalid versions and excludes `.env`, `.git`, local data, SQLite, documents,
logs, models, vectors, caches, coverage/build output, tests, ZIPs, and checksum artifacts. It
rejects allowlisted inputs that resolve outside the repository or cross a symlink/reparse-point
boundary. Repository-local output is accepted only under the excluded `dist/` directory, so the
current or a prior release can never include itself. It never includes Foundry model files.

Portable setup uses `uv sync --no-dev`; subsequent release-script `uv run` commands also pass
`--no-dev`. Developers use `uv sync`, which includes the explicit development group.

## Validation workflow

For each release candidate:

1. build the archive twice from identical source and compare ZIP bytes and SHA-256 sidecars;
2. verify the sidecar against the ZIP and inspect every member without extracting private data;
3. extract into an isolated path containing spaces;
4. run runtime-only setup and the doctor from the extracted copy;
5. start GroundNote, verify the loopback HTTP health endpoint, and test duplicate launch;
6. stop the token-scoped GroundNote session and confirm the listener is gone; and
7. delete the generated archives, extraction directory, temporary data, and runtime metadata.

Generated ZIP and checksum files are never committed. A Git tag or GitHub Release requires separate
explicit authorization.

## Future installer gate

A native installer should be reconsidered only after clean-machine testing covers supported Windows
versions, Foundry hardware variants, code signing, antivirus scanning, offline dependency staging,
upgrade/rollback behavior, user-data preservation, and third-party redistribution licenses.
