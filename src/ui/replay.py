"""Replay-mode data loading and Compare-tab rendering.

Saved runs are read from ``results/runs/qwen2.5-3b/<variant>/<scenario>.json``.
Missing files are skipped. Scoring is delegated to the frozen scorer v2
functions in :mod:`src.eval.score`; that import is lazy so simply opening the
replay tab does not load the model stack.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from src.config import RUNS_DIR, SCENARIOS_PATH
from src.ui.formatting import format_compare_column, format_reference

REPLAY_VARIANTS = ("llm", "rag", "agent_v1", "agent_v2b")
DEFAULT_RUNS_ROOT = RUNS_DIR / "qwen2.5-3b"


@lru_cache(maxsize=1)
def load_scenarios_data() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Read the frozen scenario file once (no scorer/model import)."""

    payload = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    scenarios = [dict(item) for item in payload.get("scenarios") or []]
    meta = dict(payload.get("meta") or {})
    return scenarios, meta


def categories() -> list[str]:
    """Return the category filter choices, sorted and prefixed with ``All``."""

    scenarios, _ = load_scenarios_data()
    return ["All", *sorted({str(item.get("category", "")) for item in scenarios})]


def scenario_choices(category: str | None = None) -> list[tuple[str, str]]:
    """Return ``(label, scenario_id)`` choices for the scenario dropdown."""

    scenarios, _ = load_scenarios_data()
    selected = category or "All"
    rows = [
        item
        for item in scenarios
        if selected in ("", "All") or str(item.get("category", "")) == selected
    ]
    choices: list[tuple[str, str]] = []
    for item in rows:
        message = " ".join(str(item.get("guest_message", "")).split())
        if len(message) > 105:
            message = message[:102].rstrip() + "..."
        label = f"{item.get('id', '')} · {item.get('category', '')} · {message}"
        choices.append((label, str(item.get("id", ""))))
    return choices


def scenario_by_id(scenario_id: str | None) -> dict[str, Any] | None:
    if not scenario_id:
        return None
    scenarios, _ = load_scenarios_data()
    for item in scenarios:
        if str(item.get("id")) == str(scenario_id):
            return item
    return None


def run_path(
    scenario_id: str,
    variant: str,
    runs_root: str | Path | None = None,
) -> Path:
    root = Path(runs_root) if runs_root is not None else DEFAULT_RUNS_ROOT
    return root / variant / f"{scenario_id}.json"


def load_run(
    scenario_id: str,
    variant: str,
    runs_root: str | Path | None = None,
) -> dict[str, Any] | None:
    """Load one saved run, or ``None`` when the file is absent/unreadable."""

    path = run_path(scenario_id, variant, runs_root)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _score(
    scenario: dict[str, Any],
    result: dict[str, Any],
    meta: dict[str, Any],
) -> dict[str, Any] | None:
    try:
        # Lazy: importing the scorer pulls in the frozen runner/model stack.
        from src.eval.score import score_result

        return score_result(scenario, result, meta)
    except Exception:  # pragma: no cover - defensive; a tab must not crash
        return None


def render_scenario(scenario_id: str | None) -> tuple[str, str, str, str, str]:
    """Return the reference answer plus one Markdown block per system."""

    scenario = scenario_by_id(scenario_id)
    if scenario is None:
        placeholder = "_Select a scenario to load saved runs._"
        return (format_reference(None), *(placeholder for _ in REPLAY_VARIANTS))

    _, meta = load_scenarios_data()
    columns: list[str] = []
    for variant in REPLAY_VARIANTS:
        result = load_run(str(scenario["id"]), variant)
        score = _score(scenario, result, meta) if result is not None else None
        column = format_compare_column(variant, result, score)
        if result is not None and score is None:
            column += "\n\n_Scoring could not be computed for this run._"
        columns.append(column)

    return (format_reference(scenario), *columns)


def first_scenario_id(category: str | None = None) -> str | None:
    choices = scenario_choices(category)
    return choices[0][1] if choices else None


__all__ = [
    "REPLAY_VARIANTS",
    "categories",
    "first_scenario_id",
    "load_run",
    "render_scenario",
    "run_path",
    "scenario_by_id",
    "scenario_choices",
]
