"""Read the final Stage 5 report and build the Results tab.

The report is a read-only artifact. This module does not score anything or call
a model.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config import RESULTS_DIR

REPORT_GLOB = "report_qwen2.5-3b*.json"
PREFERRED_REPORT = "report_qwen2.5-3b_all.json"

TABLE_HEADERS = [
    "Split",
    "Variant",
    "Accuracy (95% CI)",
    "Hallucination (strict)",
    "Over-escalation",
    "Median latency",
    "p95 latency",
]


def find_report(results_dir: str | Path | None = None) -> Path | None:
    """Prefer the all-split report; otherwise use the newest matching file."""

    directory = Path(results_dir) if results_dir is not None else RESULTS_DIR
    preferred = directory / PREFERRED_REPORT
    if preferred.is_file():
        return preferred
    candidates = sorted(
        directory.glob(REPORT_GLOB),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def load_report(path: str | Path | None = None) -> dict[str, Any] | None:
    report_path = Path(path) if path is not None else find_report()
    if report_path is None:
        return None
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _rate(block: Any) -> str:
    if not isinstance(block, dict):
        return "—"
    value = block.get("rate")
    return f"{float(value) * 100.0:.1f}%" if value is not None else "—"


def _latency(block: Any, key: str) -> str:
    if not isinstance(block, dict) or block.get(key) is None:
        return "—"
    return f"{float(block[key]):.1f} s"


def _accuracy(overall: dict[str, Any]) -> str:
    value = overall.get("accuracy")
    if value is None:
        return "—"
    text = f"{float(value) * 100.0:.1f}%"
    interval = overall.get("accuracy_ci95") or []
    if len(interval) == 2:
        low, high = (float(interval[0]) * 100.0, float(interval[1]) * 100.0)
        text += f" ({low:.1f}–{high:.1f})"
    n = overall.get("accuracy_n")
    if n is not None:
        text += f" · n={n}"
    return text


def table_rows(report: dict[str, Any] | None) -> list[list[str]]:
    """Build the split/variant table rows for the Results tab."""

    if not report:
        return []

    aggregates = report.get("aggregates") or {}
    variants = report.get("variants") or []
    rows: list[list[str]] = []
    for split in ("test", "all"):
        split_block = aggregates.get(split) or {}
        for variant in variants:
            overall = (split_block.get(variant) or {}).get("overall")
            if not isinstance(overall, dict):
                continue
            rows.append(
                [
                    split,
                    str(variant),
                    _accuracy(overall),
                    _rate(overall.get("hallucination_strict")),
                    _rate(overall.get("over_escalation")),
                    _latency(overall.get("latency_s"), "median"),
                    _latency(overall.get("latency_s"), "p95"),
                ]
            )
    return rows


def _fmt_p(value: Any) -> str:
    if value is None:
        return "p = n/a"
    p = float(value)
    if p == 0.0:
        return "p < 0.0001"
    if p < 0.0001:
        return f"p = {p:.2e}"
    return f"p = {p:.4f}"


def _paired(report: dict[str, Any] | None, split: str, key: str) -> Any:
    if not report:
        return None
    paired = (report.get("paired") or {}).get(split) or {}
    return (paired.get(key) or {}).get("mcnemar_exact_p")


def mcnemar_lines(report: dict[str, Any] | None) -> str:
    """Format the four McNemar p-values used in the caveat box."""

    values = [
        ("v2b vs v1, test", _paired(report, "test", "agent_v1__vs__agent_v2b")),
        ("v2b vs RAG, test", _paired(report, "test", "rag__vs__agent_v2b")),
        ("v2b vs v1, all", _paired(report, "all", "agent_v1__vs__agent_v2b")),
        ("v2b vs RAG, all", _paired(report, "all", "rag__vs__agent_v2b")),
    ]
    return "; ".join(f"{label}: {_fmt_p(value)}" for label, value in values)


def points_markdown(report: dict[str, Any] | None) -> str:
    """The fixed five-point "Read this carefully" box."""

    p_values = mcnemar_lines(report)
    return (
        "1. **Small benchmark:** 87 scenarios written by one author; 55 are the "
        "test split.\n"
        "2. **The v2b improvement over v1 and RAG is not statistically "
        f"significant.** McNemar exact p-values — {p_values}.\n"
        "3. **Scoring is automatic text matching**, validated by an oracle check "
        "and a manual review.\n"
        "4. **Planner examples were written after seeing baseline failure "
        "categories.**\n"
        "5. **3B model on a CPU:** slow, and planner JSON fails on a minority of "
        "turns."
    )


def report_caption(report: dict[str, Any] | None) -> str:
    if not report:
        return "_No report JSON found in `results/`._"
    generated = report.get("generated_at", "")
    model = report.get("model", "")
    count = report.get("scenario_count", "")
    return (
        f"Source: `{find_report().name}` · model `{model}` · "
        f"{count} scenarios · generated {generated}"
    )


__all__ = [
    "TABLE_HEADERS",
    "find_report",
    "load_report",
    "mcnemar_lines",
    "points_markdown",
    "report_caption",
    "table_rows",
]
