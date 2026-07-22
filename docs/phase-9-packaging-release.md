# Phase 9 Packaging and Release Preparation

## Scope

Phase 9 prepared the portable setup and launcher foundation for GroundNote. The current `1.0.0`
release keeps that repeatable Windows setup and local startup behavior. It does not add
a native installer, auto-updater, cloud service, telemetry, OCR, authentication, or product feature.

## User workflow

1. Install Microsoft Foundry Local and uv explicitly.
2. Run `scripts/setup_windows.ps1`.
3. Run `scripts/doctor.ps1` until the report is ready.
4. Run `scripts/start_groundnote.ps1`.
5. Stop the recorded instance with `scripts/stop_groundnote.ps1`.

All scripts resolve paths from their own location, so repository folders with spaces work and the
current shell directory is irrelevant.

## Setup behavior

Setup checks Windows, uv, and Foundry Local before running `uv sync --no-dev`. Its preparation and
doctor commands also use `uv run --no-dev`, so release setup does not install pytest, coverage,
Ruff, or mypy. It then invokes the existing application bootstrap, which creates missing
platform-local directories and applies SQLite migrations transactionally. Repeating setup is safe:
existing files, document rows, embeddings, and logs are not reset or replaced. The setup never
downloads a model.

Normal application bootstrap includes idempotent index-state reconciliation. A transient document
left by a previous process, or a Ready record whose chunks, embeddings, model metadata, and FTS
rows are inconsistent, is changed to a retryable non-searchable state. Partial embedding and FTS
data are cleared, while committed pre-embedding chunks and the GroundNote-managed copy are
preserved for explicit re-index. Unrelated complete documents are not changed.

## Doctor behavior

`python -m groundnote doctor` performs non-model checks and returns zero when no blocking errors
exist. Missing directories and a not-yet-created database are warnings when their parent is
writable. A Foundry CLI that is installed but stopped or starting is also a warning because the
launcher owns startup; the doctor does not inspect the model cache while the service is stopped.
Missing CLI/runtime, invalid configuration, unavailable runtime dependencies, inaccessible SQLite,
or an occupied requested port are errors. Missing cached model aliases are actionable warnings and
are never downloaded silently. The doctor distinguishes stopped, starting, ready, unavailable, and
unknown service states without treating `running=true` alone as Ready. It never loads or downloads
models.

## Launcher and shutdown

The launcher validates uv and Foundry Local, starts the daemon when needed, uses loopback port 8501
or the first free port through 8510, rejects duplicate sessions, and records only listener PID,
launcher PID, port, start time, and a random token. It opens the browser unless `-NoBrowser` is
supplied and cleans up the recorded process on controlled foreground shutdown.

Runtime metadata is written through a temporary token-scoped file. If directory/file creation,
metadata persistence, child startup, or the local health check fails, the launcher verifies the
session token and terminates only the listener/launcher processes created by that invocation. It
then removes partial metadata and reports a sanitized error.

The stop script validates the stored token against the exact process command line and port owner.
It never enumerates and kills all Python processes. Foundry remains unchanged by default because it
may be shared. `-StopFoundry` is an explicit user choice.

## First run

Application bootstrap creates a missing database safely and applies migrations. Empty Knowledge
Bases retain the existing helpful chat state. When Foundry is unavailable, the sidebar adds a
localized instruction to run `scripts/doctor.ps1`; model-load failures retain explicit cached-model
guidance without raw exceptions or infinite reruns.

## Data safety

The default data location remains the platform-local GroundNote application data folder. Phase 9
does not move existing data. Scripts never delete original documents or reset SQLite. Knowledge Base
Remove/Clear actions may delete only the validated GroundNote-managed copies represented by the
removed database records; original selected files remain untouched. Stale launcher metadata may be
removed only after its process identity fails verification.

## Release boundary

The deliverable is a source-based portable ZIP plus setup/launcher tooling. Foundry Local, its
execution providers, cached models, and Python runtime are external prerequisites. A native
installer is deferred until startup reliability and redistribution constraints are validated on
additional clean Windows machines.

The archive builder creates both `groundnote-1.0.0.zip` and
`groundnote-1.0.0.zip.sha256`. Release ZIP/checksum inputs are always excluded; allowlisted source
files must resolve under the repository without symlink/reparse traversal. Identical inputs retain
fixed ordering/timestamps and produce identical archive hashes.
