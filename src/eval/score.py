"""Automatic scorer for the Stage 4 baseline runs.

Run from the repository root::

    python -m src.eval.score --model qwen2.5:3b --split test
    python -m src.eval.score --model qwen2.5:3b --split all
    python -m src.eval.score --self-check

Only the ``answer`` field is scored. The deterministic sources footer that the
CLI prints is never read. Normalisation follows ``eval/scenarios.json`` and
reuses :func:`src.common.text.normalize`.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from src.agent.prompts import build_system_prompt
from src.agent.runner import model_tag
from src.agent.variants import resolve_variant
from src.common.text import normalize
from src.config import (
    PROJECT_ROOT,
    RESULTS_DIR,
    RUNS_DIR,
    SCENARIOS_PATH,
    SIMULATED_NOW,
)
from src.eval.split import SPLIT_PATH, load_split

VARIANTS = ("llm", "rag", "agent_v1", "agent_v2b")
SPLITS = ("test", "dev", "all")

_AMOUNT_RE = re.compile(r"\b(?:pkr|rs)\.?\s*(\d[\d,]*(?:\.\d+)?)", re.IGNORECASE)
_PERCENT_RE = re.compile(r"\b(\d+(?:\.\d+)?)\s?%")
_TIME_RE = re.compile(
    r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b|\b(\d{1,2}):(\d{2})\b",
    re.IGNORECASE,
)
_NUMBER_RE = re.compile(r"\b\d{3,}\b")


# ---------------------------------------------------------------------------
# Normalisation and rule primitives
# ---------------------------------------------------------------------------


_ORDINAL_SUFFIX_RE = re.compile(r"(?<=\d)(?:st|nd|rd|th)\b")
_AMPM_SPACE_RE = re.compile(r"(?<=\d)\s+(am|pm)\b")
_DASHES = str.maketrans({"\u2013": " ", "\u2014": " "})


def _norm(text: Any) -> str:
    """Scorer v2 normalisation.

    On top of :func:`src.common.text.normalize` this strips ordinal suffixes
    (``14th`` -> ``14``), removes the space between a number and am/pm
    (``8:00 pm`` -> ``8:00pm``) and treats en/em dashes as spaces. It is used
    for answers and for every alternative, so both sides get the same rules.
    ``src/common/text.normalize`` and ``eval/verify_dataset.py`` are unchanged.
    """

    value = normalize(str(text or "")).translate(_DASHES)
    value = _ORDINAL_SUFFIX_RE.sub("", value)
    value = _AMPM_SPACE_RE.sub(r"\1", value)
    return re.sub(r"\s+", " ", value).strip()


def _fact_norm(text: Any) -> str:
    """Normalise a required fact, treating ``pkr``/``rs`` as optional."""

    value = _norm(text)
    value = re.sub(r"\b(?:pkr|rs)\.?\s*", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _canon_number(value: str) -> str:
    value = value.replace(",", "").strip()
    if value.endswith(".0"):
        value = value[:-2]
    if re.fullmatch(r"\d+\.\d+", value):
        value = value.rstrip("0").rstrip(".")
    return value


def _time_minutes(hour: str, minute: str | None, ampm: str | None) -> int:
    h = int(hour)
    m = int(minute or 0)
    if ampm:
        marker = ampm.lower()
        if marker == "pm" and h != 12:
            h += 12
        elif marker == "am" and h == 12:
            h = 0
    return h * 60 + m


def _extract_numbers(text: Any) -> dict[str, str]:
    """Map canonical number token -> readable display token."""

    value = _norm(text)
    found: dict[str, str] = {}

    for match in _AMOUNT_RE.finditer(value):
        number = _canon_number(match.group(1))
        found[f"num:{number}"] = number

    for match in _PERCENT_RE.finditer(value):
        number = _canon_number(match.group(1))
        found[f"pct:{number}"] = f"{number}%"

    for match in _TIME_RE.finditer(value):
        raw = match.group(0).strip()
        if match.group(1) is not None:
            minutes = _time_minutes(match.group(1), match.group(2), match.group(3))
        else:
            minutes = _time_minutes(match.group(4), match.group(5), None)
        found[f"time:{minutes}"] = raw
        found[f"time_raw:{raw}"] = raw

    for match in _NUMBER_RE.finditer(value):
        number = _canon_number(match.group(0))
        found[f"num:{number}"] = number

    return found


def _raw_time_key(raw: str) -> str | None:
    """Canonical ``time:<minutes>`` key for a raw clock string."""

    match = _TIME_RE.search(raw)
    if not match:
        return None
    if match.group(1) is not None:
        minutes = _time_minutes(match.group(1), match.group(2), match.group(3))
    else:
        minutes = _time_minutes(match.group(4), match.group(5), None)
    return f"time:{minutes}"


def _simulated_date_tokens(now: str = SIMULATED_NOW) -> set[str]:
    tokens: set[str] = set()
    try:
        parsed = datetime.fromisoformat(now)
    except ValueError:
        return tokens
    tokens.update(
        {
            f"num:{parsed.year}",
            f"num:{parsed.month}",
            f"num:{parsed.day}",
        }
    )
    return tokens


def _forbidden_hits(scenario: dict[str, Any], answer_norm: str) -> list[str]:
    hits: list[str] = []
    for needle in scenario.get("forbidden_substrings") or []:
        if _norm(needle) and _norm(needle) in answer_norm:
            hits.append(f"substring:{needle}")
    for pattern in scenario.get("forbidden_regex") or []:
        if re.search(pattern, answer_norm, re.IGNORECASE):
            hits.append(f"regex:{pattern}")
    return hits


def _escalation(meta: dict[str, Any], answer_norm: str) -> bool:
    return any(_norm(phrase) in answer_norm for phrase in meta.get("escalation_phrases") or [])


def _manual_sections_hit(retrieved: Iterable[str], expected: Iterable[str]) -> bool:
    section_ids = [str(item) for item in retrieved]
    for target in (str(item) for item in expected):
        if any(section == target or section.startswith(target + ".") for section in section_ids):
            return True
    return False


def _guide_evidence_hit(evidence: Iterable[str], expected: Iterable[str]) -> bool:
    expected_norm = [item for item in (_norm(item) for item in expected) if item]
    if not expected_norm:
        return True
    evidence_norm = " \n ".join(_norm(item) for item in evidence)
    return all(needle in evidence_norm for needle in expected_norm)


def _tool_check(
    scenario: dict[str, Any], result: dict[str, Any]
) -> tuple[bool | None, bool | None, dict[str, Any]]:
    variant = str(result.get("variant") or "")
    if not variant.startswith("agent"):
        return None, None, {}

    calls = [call for call in result.get("tool_calls") or [] if isinstance(call, dict)]
    called = [str(call.get("name") or "") for call in calls]
    required = [str(item) for item in scenario.get("required_tools") or []]
    optional = [str(item) for item in scenario.get("optional_tools") or []]
    allowed = set(required) | set(optional)

    missing = [name for name in required if name not in called]
    extra = [name for name in called if name not in allowed]
    tool_correct = not missing and not extra

    details: dict[str, Any] = {"missing": missing, "extra": extra, "args": []}
    args_ok = True
    for name, expected in (scenario.get("expected_args") or {}).items():
        matching = [call for call in calls if str(call.get("name") or "") == name]
        if not matching:
            # The specification only checks arguments for tools that were called.
            continue
        expected = expected or {}
        satisfied = False
        for call in matching:
            args = call.get("args") or {}
            ok = True
            for field in ("check_in", "check_out", "reservation_id"):
                if field in expected and str(args.get(field)) != str(expected[field]):
                    ok = False
                    break
            if ok and "guests" in expected and expected["guests"] is not None:
                if args.get("guests") != expected["guests"]:
                    ok = False
            if ok:
                satisfied = True
                break
        if not satisfied:
            args_ok = False
            details["args"].append(
                {"tool": name, "expected": expected, "called": [call.get("args") for call in matching]}
            )

    return tool_correct, args_ok, details


def _source_check(
    scenario: dict[str, Any],
    result: dict[str, Any],
    evidence: Iterable[str],
) -> bool | None:
    variant = str(result.get("variant") or "")
    if variant.startswith("llm"):
        return None
    manual_sections = scenario.get("manual_sections") or []
    guide_evidence = scenario.get("guide_evidence") or []
    if not manual_sections and not guide_evidence:
        return None

    retrieved = result.get("retrieved") or []
    if not retrieved:
        retrieved = [
            source.get("id")
            for source in result.get("sources") or []
            if isinstance(source, dict) and source.get("type") in ("manual", "guide")
        ]

    if manual_sections and not _manual_sections_hit(retrieved, manual_sections):
        return False
    if guide_evidence and not _guide_evidence_hit(evidence, guide_evidence):
        return False
    return True


def _system_prompt_for(scenario: dict[str, Any], result: dict[str, Any]) -> str:
    context = result.get("thread_context") or scenario.get("thread_context") or {}
    variant_name = str(result.get("variant") or "llm")
    try:
        system = resolve_variant(variant_name).system
    except ValueError:
        system = "llm"
    return build_system_prompt(
        system,
        now=SIMULATED_NOW,
        guest_name=context.get("guest_name"),
        reservation_id=context.get("reservation_id"),
    )


def evaluate_answer(
    scenario: dict[str, Any],
    answer: str,
    meta: dict[str, Any],
    *,
    evidence: Iterable[str] = (),
    system_prompt: str = "",
    guest_message: str | None = None,
    thread_context: dict[str, Any] | None = None,
    check_hallucination: bool = True,
) -> dict[str, Any]:
    """Apply every text rule to one answer, without tool/source/latency data."""

    answer_norm = _norm(answer)
    facts = scenario.get("required_facts") or []

    missed_groups: list[list[str]] = []
    for group in facts:
        if not any(_fact_norm(alternative) in answer_norm for alternative in group):
            missed_groups.append(list(group))
    facts_ok = not missed_groups

    forbidden_hits = _forbidden_hits(scenario, answer_norm)
    forbidden_hit = bool(forbidden_hits)

    escalated = _escalation(meta, answer_norm)
    must_escalate = bool(scenario.get("must_escalate_to_host"))
    escalation_ok = escalated if must_escalate else True
    over_escalation = escalated and not must_escalate

    manual_review = (
        not facts
        and not must_escalate
        and bool(scenario.get("judge_rubric") or scenario.get("behavior"))
    )
    accuracy_pass: bool | None
    if manual_review:
        accuracy_pass = None
    else:
        accuracy_pass = facts_ok and not forbidden_hit and escalation_ok

    unsupported_numbers: list[str] = []
    if check_hallucination:
        allowed: dict[str, str] = {}
        allowed_texts = [
            *[str(item) for item in evidence],
            system_prompt,
            guest_message if guest_message is not None else str(scenario.get("guest_message") or ""),
            json.dumps(thread_context if thread_context is not None else scenario.get("thread_context") or {}, ensure_ascii=False),
            SIMULATED_NOW,
        ]
        for text in allowed_texts:
            allowed.update(_extract_numbers(text))
        allowed.update({token: token for token in _simulated_date_tokens()})
        allowed_text = _norm(" \n ".join(allowed_texts))

        extracted = _extract_numbers(answer)
        for key, display in extracted.items():
            if key in allowed:
                continue
            if key.startswith("time_raw:"):
                canonical = _raw_time_key(display)
                if (canonical and canonical in allowed) or display in allowed_text:
                    continue
            unsupported_numbers.append(display)
        unsupported_numbers = sorted(set(unsupported_numbers))

    hallucination_strict = forbidden_hit
    hallucination_combined = hallucination_strict or bool(unsupported_numbers)

    return {
        "facts_ok": facts_ok,
        "missed_fact_groups": missed_groups,
        "forbidden_hit": forbidden_hit,
        "forbidden_hits": forbidden_hits,
        "escalated": escalated,
        "escalation_ok": escalation_ok,
        "over_escalation": over_escalation,
        "accuracy_pass": accuracy_pass,
        "manual_review": manual_review,
        "hallucination_strict": hallucination_strict,
        "unsupported_numbers": unsupported_numbers,
        "hallucination_combined": hallucination_combined,
    }


def score_result(
    scenario: dict[str, Any],
    result: dict[str, Any],
    meta: dict[str, Any],
) -> dict[str, Any]:
    answer = str(result.get("answer") or "")
    evidence = [str(item) for item in result.get("evidence") or []]
    thread_context = result.get("thread_context") or scenario.get("thread_context") or {}
    rules = evaluate_answer(
        scenario,
        answer,
        meta,
        evidence=evidence,
        system_prompt=_system_prompt_for(scenario, result),
        guest_message=str(result.get("guest_message") or scenario.get("guest_message") or ""),
        thread_context=thread_context,
    )
    tool_correct, tool_args_ok, tool_details = _tool_check(scenario, result)
    source_hit = _source_check(scenario, result, evidence)
    return {
        "id": str(scenario["id"]),
        "variant": str(result.get("variant") or ""),
        "category": str(scenario.get("category") or ""),
        "difficulty": str(scenario.get("difficulty") or ""),
        "answer": answer,
        **rules,
        "tool_correct": tool_correct,
        "tool_args_ok": tool_args_ok,
        "tool_details": tool_details,
        "source_hit": source_hit,
        "latency_s": float(result.get("latency_s") or 0.0),
        "llm_s": float(result.get("llm_s") or 0.0),
        "tool_s": float(result.get("tool_s") or 0.0),
        "retrieval_s": float(result.get("retrieval_s") or 0.0),
        "n_llm_calls": int(result.get("n_llm_calls") or 0),
        "prompt_tokens": int(result.get("prompt_tokens") or 0),
        "completion_tokens": int(result.get("completion_tokens") or 0),
        "error": result.get("error"),
    }


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _wilson(passes: int, total: int, z: float = 1.96) -> tuple[float | None, float | None]:
    if total <= 0:
        return None, None
    p = passes / total
    denominator = 1.0 + z * z / total
    centre = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denominator
    return max(0.0, centre - margin), min(1.0, centre + margin)


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile / 100.0
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _rate(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    values = [row[key] for row in rows if row.get(key) is not None]
    if not values:
        return {"n": 0, "rate": None, "passes": 0}
    passes = sum(1 for value in values if value)
    return {"n": len(values), "rate": round(passes / len(values), 4), "passes": passes}


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    scored = [row for row in rows if row.get("accuracy_pass") is not None]
    passes = sum(1 for row in scored if row["accuracy_pass"])
    ci_low, ci_high = _wilson(passes, len(scored))
    latencies = [float(row.get("latency_s") or 0.0) for row in rows]
    tokens = [int(row.get("completion_tokens") or 0) for row in rows]
    prompt_tokens = [int(row.get("prompt_tokens") or 0) for row in rows]
    return {
        "n": len(rows),
        "accuracy_n": len(scored),
        "accuracy": round(passes / len(scored), 4) if scored else None,
        "accuracy_ci95": [round(ci_low, 4), round(ci_high, 4)] if ci_low is not None else [None, None],
        "accuracy_passes": passes,
        "manual_review_n": sum(1 for row in rows if row.get("manual_review")),
        "tool_correct": _rate(rows, "tool_correct"),
        "tool_args_ok": _rate(rows, "tool_args_ok"),
        "hallucination_strict": _rate(rows, "hallucination_strict"),
        "hallucination_combined": _rate(rows, "hallucination_combined"),
        "over_escalation": _rate(rows, "over_escalation"),
        "source_hit": _rate(rows, "source_hit"),
        "latency_s": {
            "n": len(latencies),
            "median": round(statistics.median(latencies), 3) if latencies else 0.0,
            "p95": round(_percentile(latencies, 95), 3) if latencies else 0.0,
            "mean": round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
        },
        "mean_prompt_tokens": round(sum(prompt_tokens) / len(prompt_tokens), 1) if prompt_tokens else 0.0,
        "mean_completion_tokens": round(sum(tokens) / len(tokens), 1) if tokens else 0.0,
        "errors": sum(1 for row in rows if row.get("error")),
    }


def _group(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(key) or "")].append(row)
    return {name: aggregate(group) for name, group in sorted(grouped.items())}


def _mcnemar(rows_a: list[dict[str, Any]], rows_b: list[dict[str, Any]]) -> dict[str, Any]:
    by_id_b = {row["id"]: row for row in rows_b}
    a_pass_b_fail = 0
    a_fail_b_pass = 0
    both_pass = 0
    both_fail = 0
    for row_a in rows_a:
        row_b = by_id_b.get(row_a["id"])
        if row_b is None or row_a.get("accuracy_pass") is None or row_b.get("accuracy_pass") is None:
            continue
        a = bool(row_a["accuracy_pass"])
        b = bool(row_b["accuracy_pass"])
        if a and b:
            both_pass += 1
        elif a and not b:
            a_pass_b_fail += 1
        elif not a and b:
            a_fail_b_pass += 1
        else:
            both_fail += 1
    discordant = a_pass_b_fail + a_fail_b_pass
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(math.comb(discordant, k) for k in range(0, min(a_pass_b_fail, a_fail_b_pass) + 1))
        p_value = min(1.0, 2.0 * tail / (2**discordant))
    return {
        "n_paired": both_pass + both_fail + discordant,
        "both_pass": both_pass,
        "both_fail": both_fail,
        "a_pass_b_fail": a_pass_b_fail,
        "a_fail_b_pass": a_fail_b_pass,
        "mcnemar_exact_p": round(p_value, 6),
    }


def _failure_reason(row: dict[str, Any], scenario: dict[str, Any]) -> str:
    reasons: list[str] = []
    if row.get("error"):
        reasons.append(f"error: {row['error']}")
    if row.get("missed_fact_groups"):
        groups = "; ".join(" / ".join(group) for group in row["missed_fact_groups"])
        reasons.append(f"missed facts: {groups}")
    if row.get("forbidden_hits"):
        reasons.append("forbidden: " + ", ".join(row["forbidden_hits"]))
    if scenario.get("must_escalate_to_host") and not row.get("escalated"):
        reasons.append("missing escalation")
    if row.get("tool_correct") is False:
        details = row.get("tool_details") or {}
        reasons.append(
            "tool selection: missing="
            + ",".join(details.get("missing") or [])
            + " extra="
            + ",".join(details.get("extra") or [])
        )
    if row.get("tool_args_ok") is False:
        reasons.append("tool args mismatch")
    if row.get("source_hit") is False:
        reasons.append("source miss")
    return "; ".join(reasons) or "automatic check failed"


# ---------------------------------------------------------------------------
# Loading and report construction
# ---------------------------------------------------------------------------


def load_scenarios(path: str | Path = SCENARIOS_PATH) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return list(payload["scenarios"]), dict(payload.get("meta") or {})
    return list(payload), {}


def load_result(runs_dir: str | Path, model: str, variant: str, scenario_id: str) -> dict[str, Any] | None:
    path = Path(runs_dir) / model_tag(model) / variant / f"{scenario_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def score_model(
    *,
    model: str,
    variants: Iterable[str] = VARIANTS,
    runs_dir: str | Path = RUNS_DIR,
    scenarios_path: str | Path = SCENARIOS_PATH,
    split_path: str | Path = SPLIT_PATH,
    include_details: bool = True,
    scenario_ids: Iterable[str] | None = None,
) -> dict[str, Any]:
    scenarios, meta = load_scenarios(scenarios_path)
    if scenario_ids is not None:
        wanted = {str(item) for item in scenario_ids}
        scenarios = [scenario for scenario in scenarios if str(scenario["id"]) in wanted]
    split = load_split(split_path)
    scenario_by_id = {str(scenario["id"]): scenario for scenario in scenarios}
    rows_by_variant: dict[str, list[dict[str, Any]]] = {}

    for variant in variants:
        resolved = resolve_variant(variant).name
        rows: list[dict[str, Any]] = []
        for scenario in scenarios:
            scenario_id = str(scenario["id"])
            result = load_result(runs_dir, model, resolved, scenario_id)
            if result is None:
                result = {
                    "variant": resolved,
                    "answer": "",
                    "error": "result file missing",
                    "thread_context": scenario.get("thread_context") or {},
                }
            rows.append(score_result(scenario, result, meta))
        rows_by_variant[resolved] = rows

    aggregates: dict[str, Any] = {}
    for split_name in SPLITS:
        ids = set(split["dev"] if split_name == "dev" else split["test"] if split_name == "test" else [row["id"] for rows in rows_by_variant.values() for row in rows])
        split_aggregates: dict[str, Any] = {}
        for variant, rows in rows_by_variant.items():
            selected = [row for row in rows if row["id"] in ids]
            split_aggregates[variant] = {
                "overall": aggregate(selected),
                "by_category": _group(selected, "category"),
                "by_difficulty": _group(selected, "difficulty"),
            }
        aggregates[split_name] = split_aggregates

    paired: dict[str, Any] = {}
    variant_names = list(rows_by_variant)
    for split_name in SPLITS:
        ids = set(split["dev"] if split_name == "dev" else split["test"] if split_name == "test" else [row["id"] for rows in rows_by_variant.values() for row in rows])
        split_pairs: dict[str, Any] = {}
        for index, first in enumerate(variant_names):
            for second in variant_names[index + 1 :]:
                rows_a = [row for row in rows_by_variant[first] if row["id"] in ids]
                rows_b = [row for row in rows_by_variant[second] if row["id"] in ids]
                split_pairs[f"{first}__vs__{second}"] = _mcnemar(rows_a, rows_b)
        paired[split_name] = split_pairs

    failures: list[dict[str, Any]] = []
    manual_review: list[dict[str, Any]] = []
    for variant, rows in rows_by_variant.items():
        for row in rows:
            scenario = scenario_by_id[row["id"]]
            if row.get("manual_review"):
                manual_review.append(
                    {
                        "id": row["id"],
                        "variant": variant,
                        "rubric": scenario.get("judge_rubric") or scenario.get("behavior"),
                        "answer": row["answer"],
                    }
                )
            if row.get("accuracy_pass") is False or row.get("error"):
                failures.append(
                    {
                        "id": row["id"],
                        "variant": variant,
                        "category": row["category"],
                        "difficulty": row["difficulty"],
                        "reason": _failure_reason(row, scenario),
                        "answer": row["answer"],
                    }
                )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": model,
        "model_tag": model_tag(model),
        "variants": variant_names,
        "split": split,
        "scenario_count": len(scenarios),
        "details_included": include_details,
        "aggregates": aggregates,
        "paired": paired,
        "failures": failures if include_details else [],
        "manual_review": manual_review if include_details else [],
        "per_scenario": rows_by_variant if include_details else {},
    }


# ---------------------------------------------------------------------------
# Self-checks
# ---------------------------------------------------------------------------


def oracle_check(scenarios: list[dict[str, Any]], meta: dict[str, Any]) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    passed = 0
    scored = 0
    for scenario in scenarios:
        rules = evaluate_answer(
            scenario,
            str(scenario.get("reference_answer") or ""),
            meta,
            evidence=[str(scenario.get("reference_answer") or "")],
            check_hallucination=False,
        )
        if rules["accuracy_pass"] is None:
            continue
        scored += 1
        if rules["accuracy_pass"]:
            passed += 1
        else:
            reasons = []
            if rules["missed_fact_groups"]:
                reasons.append(
                    "missed facts: "
                    + "; ".join(" / ".join(group) for group in rules["missed_fact_groups"])
                )
            if rules["forbidden_hits"]:
                reasons.append("forbidden: " + ", ".join(rules["forbidden_hits"]))
            if not rules["escalation_ok"]:
                reasons.append("missing escalation")
            failures.append({"id": scenario["id"], "reasons": reasons})
    return {
        "scored": scored,
        "passed": passed,
        "pass_rate": round(passed / scored, 4) if scored else None,
        "failures": failures,
    }


def dummy_check(
    scenarios: list[dict[str, Any]],
    meta: dict[str, Any],
    answer: str,
) -> dict[str, Any]:
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        rules = evaluate_answer(
            scenario,
            answer,
            meta,
            evidence=[answer],
            check_hallucination=False,
        )
        row = {
            "id": scenario["id"],
            "category": scenario["category"],
            "accuracy_pass": rules["accuracy_pass"],
            "over_escalation": rules["over_escalation"],
            "required_facts": len(scenario.get("required_facts") or []),
        }
        rows.append(row)
        by_category[scenario["category"]].append(row)

    def _dummy_aggregate(items: list[dict[str, Any]]) -> dict[str, Any]:
        scored = [item for item in items if item["accuracy_pass"] is not None]
        passes = sum(1 for item in scored if item["accuracy_pass"])
        return {
            "n": len(items),
            "accuracy_n": len(scored),
            "accuracy": round(passes / len(scored), 4) if scored else None,
            "passes": passes,
            "over_escalation_n": sum(1 for item in items if item["over_escalation"]),
        }

    return {
        "answer": answer,
        "overall": _dummy_aggregate(rows),
        "by_category": {
            category: _dummy_aggregate(items) for category, items in sorted(by_category.items())
        },
        "required_facts_zero": [
            row["id"] for row in rows if row["required_facts"] and row["accuracy_pass"]
        ],
    }


# ---------------------------------------------------------------------------
# Markdown / CSV output
# ---------------------------------------------------------------------------


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _main_table(aggregates: dict[str, Any], split_name: str) -> str:
    lines = [
        "| Variant | n | Accuracy (95% CI) | Tool correct | Tool args | Halluc strict | Halluc combined | Over-escalation | Source hit | Latency median / p95 / mean (s) | Tokens (prompt/completion) | Errors |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---|---|---:|",
    ]
    for variant, data in aggregates[split_name].items():
        overall = data["overall"]
        ci = overall["accuracy_ci95"]
        accuracy = (
            f"{_fmt(overall['accuracy'])} ({_fmt(ci[0])}-{_fmt(ci[1])})"
            if overall["accuracy"] is not None
            else "n/a"
        )
        latency = overall["latency_s"]
        lines.append(
            "| "
            + " | ".join(
                [
                    variant,
                    str(overall["n"]),
                    accuracy,
                    _fmt(overall["tool_correct"]["rate"]),
                    _fmt(overall["tool_args_ok"]["rate"]),
                    _fmt(overall["hallucination_strict"]["rate"]),
                    _fmt(overall["hallucination_combined"]["rate"]),
                    _fmt(overall["over_escalation"]["rate"]),
                    _fmt(overall["source_hit"]["rate"]),
                    f"{_fmt(latency['median'])} / {_fmt(latency['p95'])} / {_fmt(latency['mean'])}",
                    f"{_fmt(overall['mean_prompt_tokens'], 1)} / {_fmt(overall['mean_completion_tokens'], 1)}",
                    str(overall["errors"]),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def _category_table(aggregates: dict[str, Any], split_name: str) -> str:
    lines = [
        "| Variant | Category | n | Accuracy (95% CI) | Halluc combined | Over-escalation |",
        "|---|---|---:|---|---:|---:|",
    ]
    for variant, data in aggregates[split_name].items():
        for category, overall in data["by_category"].items():
            ci = overall["accuracy_ci95"]
            accuracy = (
                f"{_fmt(overall['accuracy'])} ({_fmt(ci[0])}-{_fmt(ci[1])})"
                if overall["accuracy"] is not None
                else "n/a"
            )
            lines.append(
                f"| {variant} | {category} | {overall['n']} | {accuracy} | "
                f"{_fmt(overall['hallucination_combined']['rate'])} | "
                f"{_fmt(overall['over_escalation']['rate'])} |"
            )
    return "\n".join(lines)


def _difficulty_table(aggregates: dict[str, Any], split_name: str) -> str:
    lines = [
        "| Variant | Difficulty | n | Accuracy (95% CI) |",
        "|---|---|---:|---|",
    ]
    for variant, data in aggregates[split_name].items():
        for difficulty, overall in data["by_difficulty"].items():
            ci = overall["accuracy_ci95"]
            accuracy = (
                f"{_fmt(overall['accuracy'])} ({_fmt(ci[0])}-{_fmt(ci[1])})"
                if overall["accuracy"] is not None
                else "n/a"
            )
            lines.append(f"| {variant} | {difficulty} | {overall['n']} | {accuracy} |")
    return "\n".join(lines)


def _paired_table(paired: dict[str, Any], split_name: str) -> str:
    lines = [
        "| Pair | n paired | A pass / B fail | A fail / B pass | Both pass | Both fail | McNemar exact p |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for pair, data in paired[split_name].items():
        lines.append(
            f"| {pair.replace('__vs__', ' vs ')} | {data['n_paired']} | "
            f"{data['a_pass_b_fail']} | {data['a_fail_b_pass']} | "
            f"{data['both_pass']} | {data['both_fail']} | {data['mcnemar_exact_p']:.4f} |"
        )
    return "\n".join(lines)


def _failure_table(failures: list[dict[str, Any]], variant: str | None = None) -> str:
    lines = [
        "| Scenario | Variant | Category | Difficulty | Reason |",
        "|---|---|---|---|---|",
    ]
    for failure in failures:
        if variant and failure["variant"] != variant:
            continue
        reason = str(failure["reason"]).replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {failure['id']} | {failure['variant']} | {failure['category']} | "
            f"{failure['difficulty']} | {reason} |"
        )
    return "\n".join(lines)


def render_markdown(report: dict[str, Any]) -> str:
    split_name = report.get("primary_split", "all")
    details = bool(report.get("details_included", True))
    sections = [
        "# Stage 5 scoring report",
        "",
        f"Generated: {report['generated_at']}",
        f"Model: `{report['model']}`",
        f"Variants: {', '.join(report['variants'])}",
        f"Primary split: {split_name}",
        "",
        "## Main results",
        "",
        _main_table(report["aggregates"], split_name),
        "",
        "## Per category",
        "",
        _category_table(report["aggregates"], split_name),
        "",
        "## Per difficulty",
        "",
        _difficulty_table(report["aggregates"], split_name),
        "",
        "## Paired comparison",
        "",
        _paired_table(report["paired"], split_name),
        "",
    ]
    if details:
        sections.extend(
            [
                "## Failure analysis",
                "",
                _failure_table(report["failures"]),
                "",
                "## Needs manual review",
                "",
            ]
        )
        for item in report["manual_review"]:
            sections.append(
                f"- {item['id']} ({item['variant']}): {item['rubric']} — answer: {item['answer'][:160]}"
            )
        sections.append("")
    else:
        sections.extend(
            [
                "## Per-scenario details",
                "",
                "Omitted: this split reports aggregates only.",
                "",
            ]
        )
    return "\n".join(sections)


def write_outputs(report: dict[str, Any], out_prefix: str | Path) -> dict[str, Path]:
    prefix = Path(out_prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    json_path = prefix.parent / f"{prefix.name}.json"
    md_path = prefix.parent / f"{prefix.name}.md"
    csv_name = prefix.name.replace("report_", "per_scenario_")
    if csv_name == prefix.name:
        csv_name = f"{prefix.name}_per_scenario"
    csv_path = prefix.parent / f"{csv_name}.csv"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")

    if not report.get("details_included", True):
        # Test/all reports are aggregates only: no per-scenario rows, no answers.
        return {"json": json_path, "md": md_path, "csv": None}

    split = report.get("split") or {}
    split_of = {scenario_id: "dev" for scenario_id in split.get("dev", [])}
    split_of.update({scenario_id: "test" for scenario_id in split.get("test", [])})
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "split",
                "id",
                "variant",
                "category",
                "difficulty",
                "accuracy_pass",
                "facts_ok",
                "missed_fact_groups",
                "forbidden_hit",
                "escalated",
                "escalation_ok",
                "over_escalation",
                "manual_review",
                "tool_correct",
                "tool_args_ok",
                "source_hit",
                "hallucination_strict",
                "unsupported_numbers",
                "hallucination_combined",
                "latency_s",
                "llm_s",
                "tool_s",
                "retrieval_s",
                "n_llm_calls",
                "prompt_tokens",
                "completion_tokens",
                "error",
                "answer",
            ]
        )
        for variant, rows in report["per_scenario"].items():
            for row in rows:
                writer.writerow(
                    [
                        split_of.get(row["id"], "all"),
                        row["id"],
                        variant,
                        row["category"],
                        row["difficulty"],
                        row["accuracy_pass"],
                        row["facts_ok"],
                        json.dumps(row["missed_fact_groups"], ensure_ascii=False),
                        row["forbidden_hit"],
                        row["escalated"],
                        row["escalation_ok"],
                        row["over_escalation"],
                        row["manual_review"],
                        row["tool_correct"],
                        row["tool_args_ok"],
                        row["source_hit"],
                        row["hallucination_strict"],
                        json.dumps(row["unsupported_numbers"], ensure_ascii=False),
                        row["hallucination_combined"],
                        row["latency_s"],
                        row["llm_s"],
                        row["tool_s"],
                        row["retrieval_s"],
                        row["n_llm_calls"],
                        row["prompt_tokens"],
                        row["completion_tokens"],
                        row["error"],
                        row["answer"],
                    ]
                )
    return {"json": json_path, "md": md_path, "csv": csv_path}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_variants(raw: str) -> list[str]:
    names = [item.strip() for item in raw.split(",") if item.strip()]
    if not names:
        raise SystemExit("At least one variant is required.")
    return [resolve_variant(name).name for name in names]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score Stage 4 baseline runs.")
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--split", choices=SPLITS, default="test")
    parser.add_argument("--variants", default=",".join(VARIANTS))
    parser.add_argument("--runs", default=str(RUNS_DIR), help="Directory containing <model_tag>/<variant>/.")
    parser.add_argument("--out-prefix", default=None, help="Output prefix; defaults to results/report_<model_tag>.")
    parser.add_argument("--self-check", action="store_true", help="Run oracle and dummy self-checks.")
    args = parser.parse_args(argv)

    if args.self_check:
        scenarios, meta = load_scenarios()
        oracle = oracle_check(scenarios, meta)
        escalate = dummy_check(scenarios, meta, "I will check with the host and get back to you.")
        empty = dummy_check(scenarios, meta, "")
        payload = {"oracle": oracle, "always_escalate": escalate, "empty": empty}
        tag = model_tag(args.model)
        path = RESULTS_DIR / f"selfcheck_{tag}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Oracle: {oracle['passed']}/{oracle['scored']} pass ({oracle['pass_rate']})")
        for failure in oracle["failures"]:
            print(f"  FAIL {failure['id']}: {'; '.join(failure['reasons'])}")
        print(f"Always escalate: {escalate['overall']}")
        print("  by category:")
        for category, data in escalate["by_category"].items():
            print(f"    {category}: {data}")
        print(f"Empty: {empty['overall']}")
        print(f"Saved {path}")
        return 0

    variants = _parse_variants(args.variants)
    include_details = args.split == "dev"
    split = load_split()
    scenario_ids = None
    if args.split in ("dev", "test"):
        scenario_ids = split[args.split]
    report = score_model(
        model=args.model,
        variants=variants,
        runs_dir=args.runs,
        include_details=include_details,
        scenario_ids=scenario_ids,
    )
    report["primary_split"] = args.split
    prefix = args.out_prefix or str(RESULTS_DIR / f"report_{model_tag(args.model)}")
    paths = write_outputs(report, prefix)
    print(
        f"Scored {len(variants)} variants on {report['scenario_count']} scenarios "
        f"(split={args.split}, details={'on' if include_details else 'aggregates only'})."
    )
    print(_main_table(report["aggregates"], args.split))
    print()
    print(_paired_table(report["paired"], args.split))
    print()
    print(f"Saved {paths['json']}")
    print(f"Saved {paths['md']}")
    if paths["csv"] is not None:
        print(f"Saved {paths['csv']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
