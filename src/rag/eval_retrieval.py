"""Retrieval evaluation against ``eval/scenarios.json``.

Run from the repository root::

    python -m src.rag.eval_retrieval

The query is the scenario's ``guest_message`` unchanged. Manual retrieval is
scored with exact-or-prefix section matching (``3`` matches ``3.6``). Guide
retrieval is scored by normalized evidence containment, with a union fallback
across the top-k chunks so the report shows where evidence is spread out.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from src.common.text import normalize
from src.rag.config import (
    CHROMA_DIR,
    EVAL_K,
    HYBRID_BM25_WEIGHT,
    HYBRID_DENSE_WEIGHT,
    HYBRID_GUIDE_MIN_DEPTH,
    HYBRID_MANUAL_MIN_DEPTH,
    MODEL_NAME,
    PROJECT_ROOT,
    RESULTS_DIR,
    RRF_K,
)
from src.rag.index import build_index, index_exists, index_stats
from src.rag.search import search_with_timing

SCENARIOS_PATH = PROJECT_ROOT / "eval" / "scenarios.json"

MANUAL_METRIC_KEYS = ("hit@1", "hit@3", "hit@5", "recall@5", "mrr")
GUIDE_METRIC_KEYS = ("hit@1", "hit@3", "hit@5", "mrr")


def _unique(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _aggregate(rows: list[dict[str, Any]], keys: Iterable[str]) -> dict[str, Any]:
    keys = tuple(keys)
    return {
        "n": len(rows),
        **{key: round(_mean([float(row[key]) for row in rows]), 4) for key in keys},
    }


def _manual_metrics(results: list[dict[str, Any]], expected: Iterable[str]) -> tuple[dict[str, Any], dict[str, int]]:
    expected_sections = _unique(expected)
    found: dict[str, int] = {}
    for rank, item in enumerate(results, start=1):
        section = str(item.get("section", ""))
        for target in expected_sections:
            if target in found:
                continue
            if section == target or section.startswith(target + "."):
                found[target] = rank

    ranks = list(found.values())
    metrics: dict[str, Any] = {
        f"hit@{cutoff}": 1.0 if any(rank <= cutoff for rank in ranks) else 0.0
        for cutoff in (1, 3, 5)
    }
    metrics["recall@5"] = len(found) / len(expected_sections) if expected_sections else 0.0
    metrics["mrr"] = 1.0 / min(ranks) if ranks else 0.0
    return metrics, found


def _guide_metrics(results: list[dict[str, Any]], evidence: Iterable[str]) -> tuple[dict[str, Any], dict[str, str | None]]:
    expected_evidence = _unique(normalize(item) for item in evidence)
    texts = [normalize(item["text"]) for item in results]

    hit_types: dict[str, str | None] = {}
    metrics: dict[str, Any] = {}
    for cutoff in (1, 3, 5):
        top = texts[:cutoff]
        single = any(all(needle in chunk_text for needle in expected_evidence) for chunk_text in top)
        union = all(any(needle in chunk_text for chunk_text in top) for needle in expected_evidence)
        metrics[f"hit@{cutoff}"] = 1.0 if (single or union) else 0.0
        hit_types[f"hit@{cutoff}"] = "single" if single else ("union" if union else None)

    first_hit = next((cutoff for cutoff in (1, 3, 5) if metrics[f"hit@{cutoff}"]), None)
    metrics["mrr"] = 1.0 / first_hit if first_hit else 0.0
    metrics["single_hit@5"] = 1.0 if hit_types["hit@5"] == "single" else 0.0
    metrics["union_hit@5"] = 1.0 if hit_types["hit@5"] == "union" else 0.0
    metrics["hit_type@5"] = hit_types["hit@5"]
    metrics["missing_evidence"] = [
        needle for needle in expected_evidence if not any(needle in text for text in texts[:5])
    ]
    return metrics, hit_types


def _retrieved_summary(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for item in results:
        summary.append(
            {
                "rank": item["rank"],
                "label": item.get("section") or item.get("heading_path") or "",
                "title": item.get("title", ""),
                "score": item["score"],
            }
        )
    return summary


def _group_by_category(details: list[dict[str, Any]], keys: Iterable[str]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for detail in details:
        grouped[detail["category"]].append(detail["metrics"])
    return {
        category: _aggregate(rows, keys)
        for category, rows in sorted(grouped.items())
    }


def _percentile(sorted_values: list[float], percentile: float) -> float:
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * percentile / 100.0
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1.0 - weight) + sorted_values[upper] * weight


def _latency(values: list[float]) -> dict[str, Any]:
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "median_ms": round(statistics.median(ordered), 2) if ordered else 0.0,
        "p95_ms": round(_percentile(ordered, 95), 2) if ordered else 0.0,
        "min_ms": round(ordered[0], 2) if ordered else 0.0,
        "max_ms": round(ordered[-1], 2) if ordered else 0.0,
    }


def _case_row(detail: dict[str, Any], *, missed: bool) -> dict[str, Any]:
    row = {
        "source": detail["source"],
        "severity": len(detail["expected"]),
        "id": detail["id"],
        "category": detail["category"],
        "query": detail["query"],
        "expected": detail["expected"],
        "miss": missed,
        "mrr": detail["metrics"]["mrr"],
        "top3": detail["retrieved"][:3],
    }
    if detail["source"] == "guide":
        row["missing_evidence"] = detail["metrics"]["missing_evidence"]
    return row


def _worst_misses(
    manual_details: list[dict[str, Any]],
    guide_details: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return up to 10 hardest cases, with real hit@5 misses first.

    When fewer than 10 queries miss at k=5, the remaining rows are the
    lowest-MRR near misses so the report still shows the ten hardest cases.
    """

    details = [*manual_details, *guide_details]
    misses = [detail for detail in details if not detail["metrics"]["hit@5"]]
    near_misses = [detail for detail in details if detail["metrics"]["hit@5"]]

    misses.sort(key=lambda detail: (-len(detail["expected"]), detail["source"], detail["id"]))
    near_misses.sort(
        key=lambda detail: (
            detail["metrics"]["mrr"],
            detail["metrics"]["hit@3"],
            detail["metrics"]["hit@1"],
            detail["source"],
            detail["id"],
        )
    )

    rows = [_case_row(detail, missed=True) for detail in misses]
    rows.extend(_case_row(detail, missed=False) for detail in near_misses)
    return rows[:10]


def evaluate(scenarios: list[dict[str, Any]], *, k: int = EVAL_K) -> dict[str, Any]:
    comparison: dict[str, Any] = {}
    latency: dict[str, Any] = {}
    worst_misses: dict[str, Any] = {}
    details_by_mode: dict[str, Any] = {}

    for mode in ("dense", "hybrid"):
        manual_details: list[dict[str, Any]] = []
        guide_details: list[dict[str, Any]] = []
        manual_latencies: list[float] = []
        guide_latencies: list[float] = []

        for scenario in scenarios:
            query = scenario["guest_message"]

            if scenario.get("manual_sections"):
                timed = search_with_timing(query, source="manual", k=k, mode=mode)
                manual_latencies.append(float(timed["timings"]["total_ms"]))
                metrics, found_ranks = _manual_metrics(timed["results"], scenario["manual_sections"])
                manual_details.append(
                    {
                        "source": "manual",
                        "id": scenario["id"],
                        "category": scenario["category"],
                        "query": query,
                        "expected": scenario["manual_sections"],
                        "metrics": metrics,
                        "found_ranks": found_ranks,
                        "retrieved": _retrieved_summary(timed["results"]),
                    }
                )

            if scenario.get("guide_evidence"):
                timed = search_with_timing(query, source="guide", k=k, mode=mode)
                guide_latencies.append(float(timed["timings"]["total_ms"]))
                metrics, hit_types = _guide_metrics(timed["results"], scenario["guide_evidence"])
                guide_details.append(
                    {
                        "source": "guide",
                        "id": scenario["id"],
                        "category": scenario["category"],
                        "query": query,
                        "expected": scenario["guide_evidence"],
                        "metrics": metrics,
                        "hit_types": hit_types,
                        "retrieved": _retrieved_summary(timed["results"]),
                    }
                )

        comparison[mode] = {
            "manual": {
                "overall": _aggregate([detail["metrics"] for detail in manual_details], MANUAL_METRIC_KEYS),
                "by_category": _group_by_category(manual_details, MANUAL_METRIC_KEYS),
            },
            "guide": {
                "overall": _aggregate([detail["metrics"] for detail in guide_details], GUIDE_METRIC_KEYS),
                "by_category": _group_by_category(guide_details, GUIDE_METRIC_KEYS),
                "union_fallback": {
                    "single_hit@5": sum(
                        1 for detail in guide_details if detail["metrics"]["hit_type@5"] == "single"
                    ),
                    "union_hit@5": sum(
                        1 for detail in guide_details if detail["metrics"]["hit_type@5"] == "union"
                    ),
                    "miss@5": sum(
                        1 for detail in guide_details if detail["metrics"]["hit_type@5"] is None
                    ),
                },
            },
        }
        latency[mode] = {
            "overall": _latency(manual_latencies + guide_latencies),
            "manual": _latency(manual_latencies),
            "guide": _latency(guide_latencies),
        }
        worst_misses[mode] = _worst_misses(manual_details, guide_details)
        details_by_mode[mode] = {
            "manual": manual_details,
            "guide": guide_details,
        }

    return {
        "comparison": comparison,
        "latency": latency,
        "worst_misses": worst_misses,
        "details": details_by_mode,
    }


def _escape(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _comparison_table(comparison: dict[str, Any]) -> str:
    lines = [
        "| Source | Category | n | Mode | hit@1 | hit@3 | hit@5 | recall@5 | MRR |",
        "|---|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for source in ("manual", "guide"):
        categories = sorted(comparison["dense"][source]["by_category"])
        for category in ["overall", *categories]:
            for mode in ("dense", "hybrid"):
                if category == "overall":
                    data = comparison[mode][source]["overall"]
                else:
                    data = comparison[mode][source]["by_category"].get(category)
                if not data:
                    continue
                recall = f"{data['recall@5']:.3f}" if "recall@5" in data else "—"
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            source.title(),
                            category,
                            str(data["n"]),
                            mode,
                            f"{data['hit@1']:.3f}",
                            f"{data['hit@3']:.3f}",
                            f"{data['hit@5']:.3f}",
                            recall,
                            f"{data['mrr']:.3f}",
                        ]
                    )
                    + " |"
                )
    return "\n".join(lines)


def _latency_table(latency: dict[str, Any]) -> str:
    lines = [
        "| Mode | Scope | Queries | Median ms | p95 ms | Min ms | Max ms |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for mode in ("dense", "hybrid"):
        for scope in ("overall", "manual", "guide"):
            data = latency[mode][scope]
            lines.append(
                f"| {mode} | {scope} | {data['n']} | {data['median_ms']:.2f} | "
                f"{data['p95_ms']:.2f} | {data['min_ms']:.2f} | {data['max_ms']:.2f} |"
            )
    return "\n".join(lines)


def _worst_table(misses: list[dict[str, Any]]) -> str:
    lines = [
        "| # | Miss? | MRR | Source | Scenario | Query | Expected | Top 3 retrieved (label — score) |",
        "|---:|---|---:|---|---|---|---|---|",
    ]
    for index, miss in enumerate(misses, start=1):
        expected = "; ".join(str(item) for item in miss["expected"])
        top3 = "; ".join(
            f"{item['label']} ({item['title']}) — {item['score']:.4f}" for item in miss["top3"]
        )
        lines.append(
            f"| {index} | {'yes' if miss['miss'] else 'near'} | {miss['mrr']:.3f} | "
            f"{miss['source']} | {_escape(miss['id'])} | {_escape(miss['query'])} | "
            f"{_escape(expected)} | {_escape(top3)} |"
        )
    return "\n".join(lines)


def _guide_hit_type_table(details: list[dict[str, Any]]) -> str:
    lines = [
        "| Scenario | Category | hit@5 type | Missing evidence |",
        "|---|---|---|---|",
    ]
    for detail in details:
        hit_type = detail["metrics"]["hit_type@5"] or "miss"
        missing = "; ".join(detail["metrics"]["missing_evidence"]) or "—"
        lines.append(
            f"| {_escape(detail['id'])} | {_escape(detail['category'])} | {hit_type} | "
            f"{_escape(missing)} |"
        )
    return "\n".join(lines)


def _index_table(build: dict[str, Any]) -> str:
    lines = [
        "| Source | Chunks | Avg words | Max words | Min words |",
        "|---|---:|---:|---:|---:|",
    ]
    for source in ("manual", "guide"):
        lines.append(
            f"| {source.title()} | {build['chunks'][source]} | {build['words'][source]['avg']:.2f} | "
            f"{build['words'][source]['max']} | {build['words'][source]['min']} |"
        )
    lines.append(
        f"| **Total** | **{build['chunks']['total']}** | — | — | — |"
    )
    return "\n".join(lines)


def _render_markdown(payload: dict[str, Any]) -> str:
    build = payload["build"]
    comparison = payload["comparison"]
    latency = payload["latency"]
    worst = payload["worst_misses"]

    build_time = (
        f"{build['build_time_s']:.3f} s" if build.get("build_time_s") is not None else "not rebuilt"
    )
    guide_dense = comparison["dense"]["guide"]["union_fallback"]
    guide_hybrid = comparison["hybrid"]["guide"]["union_fallback"]

    sections = [
        "# Retrieval evaluation",
        "",
        f"Generated: {payload['generated_at']}",
        "",
        "## Configuration",
        "",
        f"- Embedding model: `{payload['config']['model']}`",
        f"- Chroma directory: `{payload['config']['chroma_dir']}`",
        f"- Evaluation k: {payload['config']['k']}",
        f"- Hybrid fusion: weighted Reciprocal Rank Fusion, k={payload['config']['rrf_k']} "
        f"(dense weight {payload['config']['hybrid_dense_weight']}, "
        f"BM25 weight {payload['config']['hybrid_bm25_weight']})",
        f"- Hybrid candidate depth: manual {payload['config']['hybrid_manual_min_depth']}, "
        f"guide {payload['config']['hybrid_guide_min_depth']}",
        f"- Scenarios: {payload['config']['scenario_count']}",
        f"- Index build time: {build_time}",
        "",
        "## Index",
        "",
        _index_table(build),
        "",
        "## Dense vs hybrid",
        "",
        _comparison_table(comparison),
        "",
        "### Guide union fallback",
        "",
        f"- Dense: single-chunk hit@5 = {guide_dense['single_hit@5']} scenarios; "
        f"union fallback = {guide_dense['union_hit@5']}; miss@5 = {guide_dense['miss@5']}.",
        f"- Hybrid: single-chunk hit@5 = {guide_hybrid['single_hit@5']} scenarios; "
        f"union fallback = {guide_hybrid['union_hit@5']}; miss@5 = {guide_hybrid['miss@5']}.",
        "",
        "### Guide hit types (dense)",
        "",
        _guide_hit_type_table(payload["details"]["dense"]["guide"]),
        "",
        "### Guide hit types (hybrid)",
        "",
        _guide_hit_type_table(payload["details"]["hybrid"]["guide"]),
        "",
        "## Query latency",
        "",
        _latency_table(latency),
        "",
        "## 10 hardest cases (dense)",
        "",
        "True hit@5 misses first; the table is filled with the lowest-MRR near misses "
        "when fewer than 10 queries miss.",
        "",
        _worst_table(worst["dense"]),
        "",
        "## 10 hardest cases (hybrid)",
        "",
        "True hit@5 misses first; the table is filled with the lowest-MRR near misses "
        "when fewer than 10 queries miss.",
        "",
        _worst_table(worst["hybrid"]),
        "",
    ]
    return "\n".join(sections)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate dense and hybrid retrieval.")
    parser.add_argument("--no-build", action="store_true", help="Use the existing index instead of rebuilding.")
    parser.add_argument("-k", type=int, default=EVAL_K, help=f"Retrieval k (default: {EVAL_K}).")
    args = parser.parse_args(argv)

    if args.no_build:
        if not index_exists():
            print("Index missing. Run `python -m src.rag build` first, or omit --no-build.")
            return 1
        build = {"build_time_s": None, **index_stats()}
    else:
        build = build_index()

    scenarios = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))["scenarios"]
    evaluation = evaluate(scenarios, k=args.k)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "config": {
            "model": MODEL_NAME,
            "chroma_dir": str(CHROMA_DIR),
            "k": args.k,
            "rrf_k": RRF_K,
            "hybrid_dense_weight": HYBRID_DENSE_WEIGHT,
            "hybrid_bm25_weight": HYBRID_BM25_WEIGHT,
            "hybrid_manual_min_depth": HYBRID_MANUAL_MIN_DEPTH,
            "hybrid_guide_min_depth": HYBRID_GUIDE_MIN_DEPTH,
            "scenario_count": len(scenarios),
            "manual_scenarios": sum(1 for scenario in scenarios if scenario.get("manual_sections")),
            "guide_scenarios": sum(1 for scenario in scenarios if scenario.get("guide_evidence")),
        },
        "build": build,
        **evaluation,
    }

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = RESULTS_DIR / "retrieval_eval.json"
    markdown_path = RESULTS_DIR / "retrieval_eval.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(_render_markdown(payload), encoding="utf-8")

    print("Index build")
    print(f"  build time: {build.get('build_time_s')} s")
    print(
        f"  chunks: manual={build['chunks']['manual']} guide={build['chunks']['guide']} "
        f"total={build['chunks']['total']}"
    )
    print(
        f"  words: manual avg={build['words']['manual']['avg']:.2f} max={build['words']['manual']['max']}; "
        f"guide avg={build['words']['guide']['avg']:.2f} max={build['words']['guide']['max']}"
    )
    print()
    print("Dense vs hybrid")
    print(_comparison_table(payload["comparison"]))
    print()
    print("Query latency")
    print(_latency_table(payload["latency"]))
    print()
    print("10 worst misses (dense)")
    print(_worst_table(payload["worst_misses"]["dense"]))
    print()
    print(f"Saved {json_path}")
    print(f"Saved {markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
