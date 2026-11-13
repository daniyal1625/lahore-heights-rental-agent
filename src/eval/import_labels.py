"""Import and validate human labels from a review sheet.

Run from the repository root::

    python -m src.eval.import_labels --model qwen2.5:3b
    python -m src.eval.import_labels --model qwen2.5:3b --labels results/review/review_sheet_qwen2.5-3b.csv

Only rows with a ``label`` of ``pass``, ``fail`` or ``skip`` are counted.
Blank labels are reported as pending and never treated as a pass. The command
writes ``results/review/labels_<model_tag>.json`` with per-variant agreement
between the human label and the automatic ``accuracy_pass`` value, plus every
disagreement so it can be inspected in the final report.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.agent.runner import model_tag
from src.eval.review import LABELS, REVIEW_DIR, sheet_path


def _label_dir() -> Path:
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    return REVIEW_DIR


def _auto_value(raw: str) -> bool | None:
    value = (raw or "").strip().lower()
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def import_labels(
    path: str | Path,
    *,
    model: str,
) -> dict[str, Any]:
    path = Path(path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    pending: list[dict[str, str]] = []
    invalid: list[dict[str, str]] = []
    labelled: list[dict[str, Any]] = []
    for row in rows:
        raw = (row.get("label") or "").strip().lower()
        if not raw:
            pending.append({"id": row.get("id", ""), "variant": row.get("variant", "")})
            continue
        if raw not in LABELS:
            invalid.append(
                {
                    "id": row.get("id", ""),
                    "variant": row.get("variant", ""),
                    "label": row.get("label", ""),
                }
            )
            continue
        labelled.append({**row, "label": raw})

    per_variant: dict[str, dict[str, Any]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in labelled:
        grouped[str(row.get("variant") or "")].append(row)

    for variant in sorted(grouped):
        variant_rows = grouped[variant]
        auto = [
            row
            for row in variant_rows
            if row["label"] != "skip" and _auto_value(row.get("auto_accuracy_pass", "")) is not None
        ]
        agree = sum(
            1
            for row in auto
            if (row["label"] == "pass") == _auto_value(row["auto_accuracy_pass"])
        )
        disagreements = [
            {
                "id": row["id"],
                "human": row["label"],
                "auto": _auto_value(row["auto_accuracy_pass"]),
                "sample_reason": row.get("sample_reason", ""),
                "notes": row.get("notes", ""),
            }
            for row in auto
            if (row["label"] == "pass") != _auto_value(row["auto_accuracy_pass"])
        ]
        manual_only = [row for row in variant_rows if row["label"] != "skip" and _auto_value(row.get("auto_accuracy_pass", "")) is None]
        per_variant[variant] = {
            "n_labelled": len(variant_rows),
            "n_scored": len(auto),
            "n_pass": sum(1 for row in variant_rows if row["label"] == "pass"),
            "n_fail": sum(1 for row in variant_rows if row["label"] == "fail"),
            "n_skip": sum(1 for row in variant_rows if row["label"] == "skip"),
            "n_manual_only": len(manual_only),
            "n_agreement": agree,
            "agreement": round(agree / len(auto), 4) if auto else None,
            "disagreements": disagreements,
        }

    payload = {
        "model": model,
        "model_tag": model_tag(model),
        "sheet": str(path),
        "n_rows": len(rows),
        "n_labelled": len(labelled),
        "n_pending": len(pending),
        "n_invalid": len(invalid),
        "label_counts": dict(Counter(row["label"] for row in labelled)),
        "pending": pending,
        "invalid": invalid,
        "per_variant": per_variant,
    }

    out = _label_dir() / f"labels_{model_tag(model)}.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    payload["path"] = str(out)
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and summarise review-sheet labels.")
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--labels", default=None, help="Review sheet CSV; defaults to the model sheet.")
    parser.add_argument("--out", default=None, help="Optional output path for the summary JSON.")
    args = parser.parse_args(argv)

    path = Path(args.labels) if args.labels else sheet_path(args.model)
    if not path.exists():
        raise SystemExit(f"Review sheet not found: {path}. Run `python -m src.eval.review` first.")

    payload = import_labels(path, model=args.model)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["path"] = str(out)

    print(f"Read {payload['n_rows']} rows from {path}")
    print(
        f"Labelled {payload['n_labelled']}, pending {payload['n_pending']}, "
        f"invalid {payload['n_invalid']}"
    )
    for variant, data in payload["per_variant"].items():
        agreement = data["agreement"]
        print(
            f"  {variant}: labelled={data['n_labelled']} "
            f"pass={data['n_pass']} fail={data['n_fail']} skip={data['n_skip']} "
            f"manual_only={data['n_manual_only']} "
            f"agreement={agreement if agreement is not None else 'n/a'}"
        )
        for disagreement in data["disagreements"]:
            print(
                f"    DISAGREE {disagreement['id']}: human={disagreement['human']} "
                f"auto={disagreement['auto']}"
            )
    print(f"Saved {payload['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
