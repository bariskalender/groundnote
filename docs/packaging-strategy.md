# Packaging Strategy

## Decision

GroundNote `0.9.0` uses a versioned portable source archive with PowerShell setup and launcher
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
fixed timestamps. Included content is limited to runtime source, locked metadata, safe configuration
example, Streamlit configuration, user scripts, documentation, changelog, and license.

The builder rejects invalid versions and excludes `.env`, `.git`, local data, SQLite, documents,
logs, models, vectors, caches, coverage/build output, and tests. It never reads archive inputs from
outside the repository root and never includes Foundry model files.

## Future installer gate

A native installer should be reconsidered only after clean-machine testing covers supported Windows
versions, Foundry hardware variants, code signing, antivirus scanning, offline dependency staging,
upgrade/rollback behavior, user-data preservation, and third-party redistribution licenses.
