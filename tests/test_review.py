"""Review-sheet sampling and label import tests. No LLM is involved."""

from __future__ import annotations

import csv
import json

from src.eval.import_labels import import_labels
from src.eval.review import COLUMNS, SAMPLE_SIZE, build_sheet, write_sheet
from src.eval.score import load_scenarios


def _report(variants=("llm", "agent_v1")):
    scenarios, _meta = load_scenarios()
    per_scenario = {}
    for variant in variants:
        rows = []
        for index, scenario in enumerate(scenarios):
            if scenario["id"] == "D-09":
                accuracy = None
            elif scenario["id"] in ("X-06", "X-15"):
                accuracy = False
            else:
                accuracy = index % 3 != 0
            rows.append(
                {
                    "id": scenario["id"],
                    "variant": variant,
                    "category": scenario["category"],
                    "difficulty": scenario["difficulty"],
                    "answer": f"answer {scenario['id']}",
                    "accuracy_pass": accuracy,
                    "manual_review": accuracy is None,
                    "hallucination_strict": scenario["id"] == "M-02",
                    "hallucination_combined": scenario["id"] in ("M-02", "M-03"),
                    "unsupported_numbers": ["9999"] if scenario["id"] == "M-03" else [],
                    "tool_correct": None,
                    "tool_args_ok": None,
                    "source_hit": None,
                    "error": None,
                }
            )
        per_scenario[variant] = rows
    return {"variants": list(variants), "per_scenario": per_scenario}


def test_sheet_contains_manual_review_hallucinations_and_random_samples() -> None:
    scenarios, _meta = load_scenarios()
    rows = build_sheet(_report(), scenarios)

    for variant in ("llm", "agent_v1"):
        variant_rows = [row for row in rows if row["variant"] == variant]
        reasons = [row["sample_reason"] for row in variant_rows]

        assert any("manual_review" in reason for reason in reasons)
        assert any("hallucination" in reason for reason in reasons)
        assert sum("random_pass" in reason for reason in reasons) == SAMPLE_SIZE
        assert sum("random_fail" in reason for reason in reasons) == SAMPLE_SIZE

        ids = [row["id"] for row in variant_rows]
        assert len(ids) == len(set(ids)), "one row per scenario per variant"
        assert "D-09" in ids
        assert "M-02" in ids and "M-03" in ids


def test_sheet_is_deterministic() -> None:
    scenarios, _meta = load_scenarios()
    first = build_sheet(_report(), scenarios)
    second = build_sheet(_report(), scenarios)
    assert first == second


def test_sheet_round_trip_and_label_import(tmp_path, monkeypatch) -> None:
    scenarios, _meta = load_scenarios()
    rows = build_sheet(_report(), scenarios, sample_size=2)
    sheet = tmp_path / "sheet.csv"
    write_sheet(rows, sheet)

    with sheet.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == COLUMNS
        read_rows = list(reader)
    assert len(read_rows) == len(rows)

    # Leave one blank, one skip, and label the rest as the automatic value.
    for index, row in enumerate(read_rows):
        if index == 0:
            row["label"] = ""
        elif index == 1:
            row["label"] = "skip"
        elif row["auto_accuracy_pass"] == "true":
            row["label"] = "pass"
        elif row["auto_accuracy_pass"] == "false":
            row["label"] = "fail"
        else:
            row["label"] = "pass"
    with sheet.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(read_rows)

    # Keep the generated summary out of the repository: this is a test artifact,
    # and its sheet path would otherwise record the local temp directory.
    monkeypatch.setattr("src.eval.import_labels._label_dir", lambda: tmp_path)

    payload = import_labels(sheet, model="test-model")
    assert payload["n_rows"] == len(rows)
    assert (tmp_path / "labels_test-model.json").is_file()
    assert payload["n_pending"] == 1
    assert payload["n_invalid"] == 0
    assert payload["label_counts"].get("skip") == 1
    assert payload["per_variant"]["llm"]["agreement"] == 1.0
    assert json.dumps(payload)
