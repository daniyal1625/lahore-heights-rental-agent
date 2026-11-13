"""Build the human review sheet for the Stage 4 baseline runs.

Run from the repository root::

    python -m src.eval.review --model qwen2.5:3b

The sheet has one row per sampled answer, for every variant. A row is sampled
for one of four reasons:

``manual_review``
    The scenario has a ``judge_rubric`` (or ``behavior``) and is not a
    must-escalate scenario, so the automatic scorer returns ``None``.
``hallucination``
    The automatic scorer flagged the answer as a strict or combined
    hallucination.
``random_pass`` / ``random_fail``
    15 uniformly random automatic passes and 15 uniformly random automatic
    failures per variant, drawn with seed 42 from the rows not already
    sampled. Sampling is without replacement and stable across machines.

Reviewers fill the ``label`` column with ``pass``, ``fail`` or ``skip`` and may
add notes. ``python -m src.eval.import_labels`` validates and summarises the
sheet.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from src.agent.runner import model_tag
from src.config import RESULTS_DIR
from src.eval.score import VARIANTS, load_scenarios, score_model

REVIEW_DIR = RESULTS_DIR / "review"
SAMPLE_SIZE = 15
SEED = 42
LABELS = ("pass", "fail", "skip")

COLUMNS = [
    "sample_reason",
    "variant",
    "id",
    "category",
    "difficulty",
    "guest_message",
    "reference_answer",
    "judge_rubric",
    "model_answer",
    "auto_accuracy_pass",
    "auto_hallucination_strict",
    "auto_hallucination_combined",
    "unsupported_numbers",
    "auto_tool_correct",
    "auto_tool_args_ok",
    "auto_source_hit",
    "auto_error",
    "label",
    "notes",
]


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _reason_list(row: dict[str, Any], scenario: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if row.get("manual_review"):
        reasons.append("manual_review")
    if row.get("hallucination_strict") or row.get("hallucination_combined"):
        reasons.append("hallucination")
    return reasons


def build_sheet(
    report: dict[str, Any],
    scenarios: Iterable[dict[str, Any]],
    *,
    seed: int = SEED,
    sample_size: int = SAMPLE_SIZE,
) -> list[dict[str, Any]]:
    """Return the review rows for every variant in ``report``."""

    scenario_by_id = {str(scenario["id"]): scenario for scenario in scenarios}
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []

    for variant in report.get("variants") or VARIANTS:
        variant_rows = report["per_scenario"].get(variant) or []
        chosen: dict[str, list[str]] = defaultdict(list)

        for row in variant_rows:
            scenario = scenario_by_id[row["id"]]
            for reason in _reason_list(row, scenario):
                chosen[row["id"]].append(reason)

        already = set(chosen)
        passes = [
            row["id"]
            for row in variant_rows
            if row.get("accuracy_pass") is True and row["id"] not in already
        ]
        fails = [
            row["id"]
            for row in variant_rows
            if row.get("accuracy_pass") is False and row["id"] not in already
        ]
        for reason, pool in (("random_pass", passes), ("random_fail", fails)):
            sample = sorted(rng.sample(pool, min(sample_size, len(pool))))
            for scenario_id in sample:
                chosen[scenario_id].append(reason)

        row_by_id = {row["id"]: row for row in variant_rows}
        for scenario_id in sorted(chosen):
            row = row_by_id[scenario_id]
            scenario = scenario_by_id[scenario_id]
            rows.append(
                {
                    "sample_reason": ";".join(chosen[scenario_id]),
                    "variant": variant,
                    "id": scenario_id,
                    "category": row.get("category") or "",
                    "difficulty": row.get("difficulty") or "",
                    "guest_message": scenario.get("guest_message") or "",
                    "reference_answer": scenario.get("reference_answer") or "",
                    "judge_rubric": scenario.get("judge_rubric")
                    or scenario.get("behavior")
                    or "",
                    "model_answer": row.get("answer") or "",
                    "auto_accuracy_pass": _fmt(row.get("accuracy_pass")),
                    "auto_hallucination_strict": _fmt(row.get("hallucination_strict")),
                    "auto_hallucination_combined": _fmt(row.get("hallucination_combined")),
                    "unsupported_numbers": _fmt(row.get("unsupported_numbers")),
                    "auto_tool_correct": _fmt(row.get("tool_correct")),
                    "auto_tool_args_ok": _fmt(row.get("tool_args_ok")),
                    "auto_source_hit": _fmt(row.get("source_hit")),
                    "auto_error": _fmt(row.get("error")),
                    "label": "",
                    "notes": "",
                }
            )

    return rows


def write_sheet(rows: list[dict[str, Any]], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: _fmt(row.get(column)) for column in COLUMNS})
    return path


def sheet_path(model: str) -> Path:
    return REVIEW_DIR / f"review_sheet_{model_tag(model)}.csv"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the human review sheet.")
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--variants", default=",".join(VARIANTS))
    parser.add_argument("--report", default=None, help="Existing report JSON to reuse.")
    parser.add_argument("--out", default=None, help="Output CSV path.")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--sample-size", type=int, default=SAMPLE_SIZE)
    args = parser.parse_args(argv)

    scenarios, _meta = load_scenarios()
    if args.report:
        report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    else:
        variants = [item.strip() for item in args.variants.split(",") if item.strip()]
        report = score_model(model=args.model, variants=variants)

    rows = build_sheet(report, scenarios, seed=args.seed, sample_size=args.sample_size)
    out = Path(args.out) if args.out else sheet_path(args.model)
    write_sheet(rows, out)

    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[str(row["sample_reason"])] += 1
    print(f"Wrote {out} ({len(rows)} rows)")
    for reason, count in sorted(counts.items()):
        print(f"  {reason}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
