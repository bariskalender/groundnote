"""GroundNote command-line utilities for setup and release preparation."""

from __future__ import annotations

import argparse
from pathlib import Path

from groundnote import __version__
from groundnote.bootstrap import initialize_application
from groundnote.diagnostics import DEFAULT_PORT, run_doctor
from groundnote.release import archive_members, build_release_archive, checksum_path_for


def main() -> int:
    parser = argparse.ArgumentParser(prog="groundnote")
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor_parser = subparsers.add_parser("doctor", help="Check local environment readiness.")
    doctor_parser.add_argument("--port", type=int, default=DEFAULT_PORT)

    subparsers.add_parser("prepare", help="Create local directories and initialize SQLite safely.")

    archive_parser = subparsers.add_parser(
        "build-archive", help="Build a privacy-safe portable source archive."
    )
    archive_parser.add_argument("--output-directory", type=Path, default=Path("dist"))

    args = parser.parse_args()
    if args.command == "doctor":
        report = run_doctor(port=args.port)
        print(report.render())
        return report.exit_code
    if args.command == "prepare":
        initialize_application()
        print("GroundNote local directories and database are ready.")
        return 0
    if args.command == "build-archive":
        repository_root = Path(__file__).resolve().parents[2]
        archive = build_release_archive(repository_root, args.output_directory)
        checksum = checksum_path_for(archive)
        print(
            f"Created {archive.name} with {len(archive_members(archive))} files and "
            f"{checksum.name}."
        )
        return 0
    parser.error("Unknown command.")


if __name__ == "__main__":
    raise SystemExit(main())
