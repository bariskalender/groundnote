"""Benchmark the lightweight GroundNote Foundry Local model candidates."""

from __future__ import annotations

import json
import math
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import psutil

from groundnote.ai.foundry_chat import FoundryChatProvider
from groundnote.ai.foundry_embeddings import FoundryEmbeddingProvider
from groundnote.ai.foundry_manager import FoundryManager
from groundnote.ai.models import ChatMessage

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FOUNDARY_DATA_DIR = PROJECT_ROOT / ".foundry-local"
DOCS_DIR = PROJECT_ROOT / "docs"
BENCHMARK_JSON = DOCS_DIR / "model-benchmark-results.json"
BENCHMARK_MD = DOCS_DIR / "model-benchmark.md"

CHAT_CANDIDATES = ("phi-3.5-mini", "qwen2.5-0.5b")
EMBEDDING_CANDIDATE = "qwen3-embedding-0.6b"


def main() -> int:
    DOCS_DIR.mkdir(exist_ok=True)
    manager = FoundryManager(
        app_name="groundnote_phase1_benchmark",
        app_data_dir=FOUNDARY_DATA_DIR / "app",
        model_cache_dir=FOUNDARY_DATA_DIR / "model-cache",
        logs_dir=FOUNDARY_DATA_DIR / "logs",
    )
    process = psutil.Process()
    available = {model.alias: model for model in manager.list_models()}

    results: dict[str, Any] = {
        "created_at": datetime.now(UTC).isoformat(),
        "notes": [
            "Model download requires internet on first run.",
            "Cached inference is expected to work offline after local model files are available.",
            "No cloud API was used.",
            "Models were loaded sequentially.",
            "CLI catalog may list GPU aliases; this SDK benchmark records the selected runtime.",
        ],
        "available_candidate_aliases": {
            alias: alias in available for alias in (*CHAT_CANDIDATES, EMBEDDING_CANDIDATE)
        },
        "chat": [],
        "embedding": None,
        "decision": None,
    }

    for alias in CHAT_CANDIDATES:
        if alias not in available:
            results["chat"].append({"alias": alias, "available": False})
            continue
        results["chat"].append(benchmark_chat(alias, manager, process))

    if EMBEDDING_CANDIDATE in available:
        results["embedding"] = benchmark_embedding(EMBEDDING_CANDIDATE, manager, process)
    else:
        results["embedding"] = {"alias": EMBEDDING_CANDIDATE, "available": False}

    results["decision"] = choose_models(results)
    BENCHMARK_JSON.write_text(json.dumps(results, indent=2), encoding="utf-8")
    BENCHMARK_MD.write_text(render_markdown(results), encoding="utf-8")
    print(json.dumps(results, indent=2))
    return 0


def benchmark_chat(alias: str, manager: FoundryManager, process: psutil.Process) -> dict[str, Any]:
    provider = FoundryChatProvider(alias, manager)
    before = manager.get_model_info(alias)
    result: dict[str, Any] = {
        "alias": alias,
        "available": True,
        "before": asdict(before),
        "downloaded_during_benchmark": False,
        "download_seconds": None,
        "load_seconds": None,
        "first_response_seconds": None,
        "total_response_seconds": None,
        "rss_mb_before_load": rss_mb(process),
        "rss_mb_after_load": None,
        "response_text": "",
        "trivial_prompt_passed": False,
        "unload_succeeded": False,
        "error": None,
    }

    try:
        if not before.is_cached:
            start = time.perf_counter()
            provider.ensure_model_available(download=True)
            result["download_seconds"] = elapsed(start)
            result["downloaded_during_benchmark"] = True

        start = time.perf_counter()
        provider.load()
        result["load_seconds"] = elapsed(start)
        result["rss_mb_after_load"] = rss_mb(process)

        prompt = "What is 2 + 2? Reply with only the digit."
        start = time.perf_counter()
        completion = provider.generate([ChatMessage(role="user", content=prompt)], max_tokens=8)
        total = elapsed(start)
        text = completion.text.strip()
        result["first_response_seconds"] = total
        result["total_response_seconds"] = total
        result["response_text"] = text[:200]
        result["trivial_prompt_passed"] = "4" in text
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        try:
            provider.unload()
            result["unload_succeeded"] = True
        except Exception as exc:
            result["unload_error"] = f"{type(exc).__name__}: {exc}"

    result["after"] = asdict(manager.get_model_info(alias))
    return result


def benchmark_embedding(
    alias: str,
    manager: FoundryManager,
    process: psutil.Process,
) -> dict[str, Any]:
    provider = FoundryEmbeddingProvider(alias, manager)
    before = manager.get_model_info(alias)
    result: dict[str, Any] = {
        "alias": alias,
        "available": True,
        "before": asdict(before),
        "downloaded_during_benchmark": False,
        "download_seconds": None,
        "load_seconds": None,
        "batch_embedding_seconds": None,
        "rss_mb_before_load": rss_mb(process),
        "rss_mb_after_load": None,
        "dimension": None,
        "finite_values": False,
        "cosine_same_text": None,
        "cosine_different_text": None,
        "sanity_test_passed": False,
        "unload_succeeded": False,
        "error": None,
    }

    try:
        if not before.is_cached:
            start = time.perf_counter()
            provider.ensure_model_available(download=True)
            result["download_seconds"] = elapsed(start)
            result["downloaded_during_benchmark"] = True

        start = time.perf_counter()
        provider.load()
        result["load_seconds"] = elapsed(start)
        result["rss_mb_after_load"] = rss_mb(process)

        texts = [
            "Paris is the capital of France.",
            "Paris is the capital of France.",
            "Rust owns memory safely.",
        ]
        start = time.perf_counter()
        embeddings = provider.embed_many(texts, batch_size=3)
        result["batch_embedding_seconds"] = elapsed(start)
        result["dimension"] = embeddings.dimension
        result["finite_values"] = bool(np.all(np.isfinite(embeddings.vectors)))
        same = cosine(embeddings.vectors[0], embeddings.vectors[1])
        different = cosine(embeddings.vectors[0], embeddings.vectors[2])
        result["cosine_same_text"] = same
        result["cosine_different_text"] = different
        result["sanity_test_passed"] = bool(result["finite_values"] and same > different)
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        try:
            provider.unload()
            result["unload_succeeded"] = True
        except Exception as exc:
            result["unload_error"] = f"{type(exc).__name__}: {exc}"

    result["after"] = asdict(manager.get_model_info(alias))
    return result


def choose_models(results: dict[str, Any]) -> dict[str, str | None]:
    successful_chat = [
        item
        for item in results["chat"]
        if item.get("available") and item.get("trivial_prompt_passed") and not item.get("error")
    ]
    successful_aliases = {item["alias"] for item in successful_chat}
    default_chat = "phi-3.5-mini" if "phi-3.5-mini" in successful_aliases else None
    fallback_chat = "qwen2.5-0.5b" if "qwen2.5-0.5b" in successful_aliases else None
    if default_chat is None and successful_chat:
        default_chat = successful_chat[0]["alias"]
    embedding = results["embedding"] or {}
    embedding_alias = (
        EMBEDDING_CANDIDATE
        if embedding.get("sanity_test_passed") and not embedding.get("error")
        else None
    )
    return {
        "default_chat_model": default_chat,
        "fallback_chat_model": fallback_chat,
        "embedding_model": embedding_alias,
    }


def render_markdown(results: dict[str, Any]) -> str:
    lines = [
        "# GroundNote Model Benchmark",
        "",
        f"Created at: `{results['created_at']}`",
        "",
        "## Safety Notes",
        "",
        "- Model download requires internet on first run.",
        "- Cached inference should work offline after local model files are available.",
        "- No cloud API was used.",
        "- Models were loaded sequentially; no stress test was run.",
        "- The CLI catalog may list GPU aliases, but this SDK benchmark records the selected "
        "runtime from the SDK.",
        "",
        "## Chat Candidates",
        "",
        "| Alias | Cached before | Download s | Load s | Response s | RSS before MB | "
        "RSS after MB | Passed | Error |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for item in results["chat"]:
        before = item.get("before") or {}
        lines.append(
            "| {alias} | {cached} | {download} | {load} | {response} | {rss_before} | "
            "{rss_after} | {passed} | {error} |".format(
                alias=item.get("alias"),
                cached=before.get("is_cached"),
                download=format_value(item.get("download_seconds")),
                load=format_value(item.get("load_seconds")),
                response=format_value(item.get("total_response_seconds")),
                rss_before=format_value(item.get("rss_mb_before_load")),
                rss_after=format_value(item.get("rss_mb_after_load")),
                passed=item.get("trivial_prompt_passed"),
                error=item.get("error") or "",
            )
        )

    embedding = results.get("embedding") or {}
    lines.extend(
        [
            "",
            "## Embedding Candidate",
            "",
            "| Alias | Cached before | Download s | Load s | Batch s | Dimension | Same cosine | "
            "Different cosine | Passed | Error |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
            (
                "| {alias} | {cached} | {download} | {load} | {batch} | {dimension} | "
                "{same} | {different} | {passed} | {error} |"
            ).format(
                alias=embedding.get("alias"),
                cached=(embedding.get("before") or {}).get("is_cached"),
                download=format_value(embedding.get("download_seconds")),
                load=format_value(embedding.get("load_seconds")),
                batch=format_value(embedding.get("batch_embedding_seconds")),
                dimension=embedding.get("dimension"),
                same=format_value(embedding.get("cosine_same_text")),
                different=format_value(embedding.get("cosine_different_text")),
                passed=embedding.get("sanity_test_passed"),
                error=embedding.get("error") or "",
            ),
            "",
            "## Model Decision",
            "",
            f"- Default chat model: `{results['decision']['default_chat_model']}`",
            f"- Low-resource fallback chat model: `{results['decision']['fallback_chat_model']}`",
            f"- Embedding model: `{results['decision']['embedding_model']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def rss_mb(process: psutil.Process) -> float:
    return round(process.memory_info().rss / (1024 * 1024), 2)


def elapsed(start: float) -> float:
    return round(time.perf_counter() - start, 3)


def cosine(left: np.ndarray, right: np.ndarray) -> float:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    if denominator == 0 or not math.isfinite(denominator):
        return 0.0
    return round(float(np.dot(left, right) / denominator), 6)


def format_value(value: object) -> str:
    if value is None:
        return ""
    return str(value)


if __name__ == "__main__":
    raise SystemExit(main())
