"""Batch runner used by ``python -m src.agent run``.

The runner is deliberately scoring-free: it writes one JSON file per
scenario/system and resumes by skipping files that already exist.
"""

from __future__ import annotations

import ctypes
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable

from src.agent.systems import RunResult
from src.agent.systems import run as run_system
from src.agent.variants import resolve_variant
from src.config import (
    KEEP_ALIVE,
    MAX_TOOL_ROUNDS,
    MODEL,
    NUM_CTX,
    NUM_PREDICT,
    OLLAMA_HOST,
    PROJECT_ROOT,
    RAG_GUIDE_K,
    RAG_MANUAL_K,
    RAG_MODE,
    REQUEST_TIMEOUT_S,
    RUNS_DIR,
    SCENARIOS_PATH,
    SEED,
    SIMULATED_NOW,
    TEMPERATURE,
    TOOL_SEARCH_K,
)
from src.eval.split import SPLIT_PATH, load_split

RunFunction = Callable[..., Awaitable[RunResult]]


def model_tag(model: str) -> str:
    """Turn ``qwen2.5:3b`` into a filesystem-safe directory name."""

    tag = re.sub(r"[^A-Za-z0-9._-]+", "-", model).strip("-.")
    return tag or "model"


def result_path(out_dir: str | Path, model: str, system: str, scenario_id: str) -> Path:
    """Return the explicit-variant path, resolving the ``agent`` alias."""

    variant = resolve_variant(system)
    return Path(out_dir) / model_tag(model) / variant.name / f"{scenario_id}.json"


def load_scenarios(path: str | Path = SCENARIOS_PATH) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    scenarios = payload["scenarios"] if isinstance(payload, dict) else payload
    if not isinstance(scenarios, list):
        raise ValueError(f"Unexpected scenarios payload in {path}")
    return scenarios


def select_scenarios(
    scenarios: list[dict[str, Any]],
    *,
    ids: list[str] | None = None,
    category: str | None = None,
    split: str | None = None,
    split_path: str | Path = SPLIT_PATH,
    all_: bool = False,
) -> list[dict[str, Any]]:
    if split:
        if split == "all":
            return list(scenarios)
        if split not in ("dev", "test"):
            raise ValueError(f"Unknown split {split!r}. Use dev, test or all.")
        split_ids = list(load_split(split_path)[split])
        return select_scenarios(scenarios, ids=split_ids)

    if ids:
        wanted = list(dict.fromkeys(ids))
        by_id = {scenario["id"]: scenario for scenario in scenarios}
        missing = [scenario_id for scenario_id in wanted if scenario_id not in by_id]
        if missing:
            raise ValueError(f"Unknown scenario ids: {', '.join(missing)}")
        return [by_id[scenario_id] for scenario_id in wanted]

    if category:
        selected = [scenario for scenario in scenarios if scenario.get("category") == category]
        if not selected:
            categories = sorted({str(scenario.get("category")) for scenario in scenarios})
            raise ValueError(f"Unknown category {category!r}. Available: {', '.join(categories)}")
        return selected

    if all_:
        return list(scenarios)

    raise ValueError("Choose --ids, --category or --all.")


async def run_batch(
    scenarios: list[dict[str, Any]],
    systems: list[str],
    *,
    model: str,
    out_dir: str | Path = RUNS_DIR,
    force: bool = False,
    progress: Callable[[str], None] | None = None,
    run_fn: RunFunction = run_system,
) -> dict[str, Any]:
    """Run every scenario/system pair, skipping files unless ``force``."""

    emit = progress or (lambda message: None)
    variant_names = [resolve_variant(system).name for system in systems]
    total = len(scenarios) * len(variant_names)
    completed = 0
    skipped = 0
    failed = 0
    errors: list[dict[str, str]] = []
    started = time.perf_counter()

    for scenario in scenarios:
        scenario_id = str(scenario["id"])
        for system in variant_names:
            path = result_path(out_dir, model, system, scenario_id)
            if path.exists() and not force:
                skipped += 1
                emit(f"[skip] {scenario_id} {system}: {path}")
                continue

            result = await run_fn(
                system,
                scenario["guest_message"],
                scenario.get("thread_context") or {},
                model=model,
            )
            result.scenario_id = scenario_id
            if not result.variant:
                result.variant = resolve_variant(system).name

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            completed += 1
            if result.error:
                failed += 1
                errors.append(
                    {"scenario_id": scenario_id, "variant": result.variant, "error": result.error}
                )

            elapsed = time.perf_counter() - started
            remaining = total - completed - skipped
            eta = (elapsed / completed) * remaining if completed else 0.0
            status = "error" if result.error else "ok"
            emit(
                f"[{completed + skipped}/{total}] {scenario_id} {system} "
                f"{status} {result.latency_s:.1f}s "
                f"calls={result.n_llm_calls} tools={len(result.tool_calls)} "
                f"eta={eta / 60:.1f}m"
            )

    return {
        "total": total,
        "completed": completed,
        "skipped": skipped,
        "failed": failed,
        "errors": errors,
        "elapsed_s": round(time.perf_counter() - started, 3),
    }


def _cpu_name() -> str:
    if os.name == "nt":
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            value, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            return str(value).strip()
        except Exception:  # noqa: BLE001 - metadata is best-effort
            pass
    return platform.processor() or platform.machine() or "unknown"


def _ram_bytes() -> int:
    if os.name == "nt":
        try:
            class MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatusEx()
            status.dwLength = ctypes.sizeof(MemoryStatusEx)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return int(status.ullTotalPhys)
        except Exception:  # noqa: BLE001
            pass
    try:
        return int(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"))
    except (AttributeError, ValueError, OSError):
        return 0


def _package_versions() -> dict[str, str]:
    packages = [
        "fastapi",
        "uvicorn",
        "faker",
        "pytest",
        "httpx",
        "torch",
        "sentence-transformers",
        "chromadb",
        "rank-bm25",
        "langchain-core",
        "langchain-ollama",
        "langgraph",
        "pydantic",
        "numpy",
    ]
    versions: dict[str, str] = {}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not installed"
    return versions


def code_hash(root: str | Path = PROJECT_ROOT) -> dict[str, Any]:
    """SHA-256 over every ``src/**/*.py`` file, path-separated for stability."""

    root = Path(root)
    digest = hashlib.sha256()
    files = sorted(
        path for path in (root / "src").rglob("*.py") if "__pycache__" not in path.parts
    )
    for path in files:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return {"sha256": digest.hexdigest(), "files": len(files)}


async def build_run_meta(
    *,
    model: str,
    variants: list[str],
    split: str,
    scenario_count: int,
    started_at: str,
    ended_at: str | None,
    warmup: dict[str, Any] | None,
    summary: dict[str, Any] | None,
) -> dict[str, Any]:
    """Collect machine, package, model and code metadata for a run."""

    from src.agent.systems import ollama_metadata

    ollama_version, digest = await ollama_metadata(model)
    ram = _ram_bytes()
    return {
        "model": model,
        "model_tag": model_tag(model),
        "variants": variants,
        "split": split,
        "scenario_count": scenario_count,
        "started_at": started_at,
        "ended_at": ended_at,
        "simulated_now": SIMULATED_NOW,
        "machine": {
            "cpu": _cpu_name(),
            "ram_bytes": ram,
            "ram_gib": round(ram / (1024**3), 2) if ram else None,
            "os": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "python": {
            "version": sys.version,
            "version_info": list(sys.version_info[:3]),
            "implementation": platform.python_implementation(),
            "executable": sys.executable,
        },
        "packages": _package_versions(),
        "ollama": {
            "host": OLLAMA_HOST,
            "version": ollama_version,
            "model": model,
            "digest": digest,
            "options": {
                "temperature": TEMPERATURE,
                "seed": SEED,
                "num_ctx": NUM_CTX,
                "num_predict": NUM_PREDICT,
                "keep_alive": KEEP_ALIVE,
                "request_timeout_s": REQUEST_TIMEOUT_S,
                "max_tool_rounds": MAX_TOOL_ROUNDS,
            },
        },
        "retrieval": {
            "mode": RAG_MODE,
            "rag_manual_k": RAG_MANUAL_K,
            "rag_guide_k": RAG_GUIDE_K,
            "tool_search_k": TOOL_SEARCH_K,
        },
        "code": code_hash(),
        "warmup": warmup,
        "summary": summary,
    }


def write_run_meta(out_dir: str | Path, model: str, payload: dict[str, Any]) -> Path:
    path = Path(out_dir) / model_tag(model) / "run_meta.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
