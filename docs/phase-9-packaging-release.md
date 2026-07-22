# Phase 9 Packaging and Release Preparation

## Scope

Phase 9 prepares GroundNote `0.9.0` for repeatable Windows setup and local startup. It does not add
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

Setup checks Windows, uv, and Foundry Local before running `uv sync`. It then invokes the existing
application bootstrap, which creates missing platform-local directories and applies SQLite
migrations transactionally. Repeating setup is safe: existing files, document rows, embeddings,
and logs are not reset or replaced. The setup never downloads a model.

## Doctor behavior

`python -m groundnote doctor` performs non-model checks and returns zero only when no blocking
errors exist. Missing directories and a not-yet-created database are warnings when their parent is
writable. Missing CLI/runtime, stopped Foundry service, missing required cached models, invalid
configuration, unavailable dependencies, inaccessible SQLite, or an occupied requested port are
errors.

The installed Foundry Local CLI `0.10.2` starts its daemon while inspecting the cache. If the doctor
finds the server initially stopped, it restores that stopped state after cache inspection. It never
loads or downloads models.

## Launcher and shutdown

The launcher validates uv and Foundry Local, starts the daemon when needed, uses loopback port 8501
or the first free port through 8510, rejects duplicate sessions, and records only listener PID,
launcher PID, port, start time, and a random token. It opens the browser unless `-NoBrowser` is
supplied and cleans up the recorded process on controlled foreground shutdown.

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
does not move existing data. Scripts never delete original documents or reset SQLite. Only stale
launcher metadata may be removed after its process identity fails verification.

## Release boundary

The deliverable is a source-based portable ZIP plus setup/launcher tooling. Foundry Local, its
execution providers, cached models, and Python runtime are external prerequisites. A native
installer is deferred until startup reliability and redistribution constraints are validated on
additional clean Windows machines.
