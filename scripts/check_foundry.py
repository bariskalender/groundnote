"""Check local Foundry Local readiness without downloading models."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from importlib import metadata
from pathlib import Path
from typing import Any

from groundnote.ai.foundry_manager import FoundryManager

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FOUNDARY_DATA_DIR = PROJECT_ROOT / ".foundry-local"


def main() -> int:
    result: dict[str, Any] = {
        "os": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
        },
        "python_version": platform.python_version(),
        "uv_version": run_text([find_executable("uv"), "--version"]),
        "foundry_cli_path": shutil.which("foundry"),
        "foundry_version": run_text(["foundry", "--version"]),
        "foundry_status": run_text(["foundry", "status"]),
        "foundry_server_status": run_text(["foundry", "server", "status"]),
        "nvidia_gpu": run_text(
            [
                "nvidia-smi",
                "--query-gpu=name,driver_version,memory.total,memory.free",
                "--format=csv,noheader",
            ]
        ),
        "sdk": {},
        "models": {},
    }

    for package_name in ("foundry-local-sdk-winml", "foundry-local-sdk", "openai"):
        result["sdk"][package_name] = package_version(package_name)

    try:
        manager = FoundryManager(
            app_name="groundnote_phase1_check",
            app_data_dir=FOUNDARY_DATA_DIR / "app",
            model_cache_dir=FOUNDARY_DATA_DIR / "model-cache",
            logs_dir=FOUNDARY_DATA_DIR / "logs",
        )
        models = manager.list_models()
        result["models"]["count"] = len(models)
        result["models"]["aliases"] = sorted({model.alias for model in models})
        result["models"]["candidates"] = {
            alias: next((model.__dict__ for model in models if model.alias == alias), None)
            for alias in ("phi-3.5-mini", "qwen2.5-0.5b", "qwen3-embedding-0.6b")
        }
    except Exception as exc:
        result["models"]["error"] = f"{type(exc).__name__}: {exc}"

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if "error" not in result["models"] else 1


def run_text(command: list[str], timeout_seconds: int = 60) -> dict[str, Any]:
    if shutil.which(command[0]) is None and not Path(command[0]).exists():
        return {"available": False, "output": ""}

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return {"available": True, "timeout": True, "output": str(exc)}

    output_parts = (completed.stdout.strip(), completed.stderr.strip())
    output = "\n".join(part for part in output_parts if part)
    return {"available": True, "returncode": completed.returncode, "output": output}


def package_version(package_name: str) -> str | None:
    try:
        return metadata.version(package_name)
    except metadata.PackageNotFoundError:
        return None


def find_executable(name: str) -> str:
    path = shutil.which(name)
    if path is not None:
        return path
    local_bin = Path(os.environ.get("USERPROFILE", "")) / ".local" / "bin" / f"{name}.exe"
    if local_bin.exists():
        return str(local_bin)
    return name


if __name__ == "__main__":
    raise SystemExit(main())
