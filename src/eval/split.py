"""Deterministic, category-stratified dev/test split.

Run from the repository root::

    python -m src.eval.split            # write eval/split.json and print counts
    python -m src.eval.split --check    # verify the checked-in split only

The split is deliberately tiny and dependency-free so it can be regenerated
exactly: one ``random.Random(seed)`` shuffles each sorted category, then the
first ``round(n * dev_fraction)`` ids (at least one, never all) become dev.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from src.config import PROJECT_ROOT, SCENARIOS_PATH

SPLIT_PATH = PROJECT_ROOT / "eval" / "split.json"
SEED = 42
DEV_FRACTION = 0.35


def load_scenarios(path: str | Path = SCENARIOS_PATH) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    scenarios = payload["scenarios"] if isinstance(payload, dict) else payload
    if not isinstance(scenarios, list):
        raise ValueError(f"Unexpected scenarios payload in {path}")
    return scenarios


def build_split(
    scenarios: Iterable[dict[str, Any]],
    *,
    seed: int = SEED,
    dev_fraction: float = DEV_FRACTION,
) -> dict[str, Any]:
    """Return ``{"seed": seed, "dev": [...], "test": [...]}``.

    Every category contributes at least one dev and one test scenario whenever
    it has at least two scenarios. The result is sorted by id so the JSON is
    stable across runs and machines.
    """

    by_category: dict[str, list[str]] = defaultdict(list)
    for scenario in scenarios:
        by_category[str(scenario["category"])].append(str(scenario["id"]))

    rng = random.Random(seed)
    dev: list[str] = []
    test: list[str] = []
    for category in sorted(by_category):
        ids = sorted(by_category[category])
        if len(ids) < 2:
            raise ValueError(f"Category {category!r} needs at least 2 scenarios to split.")
        rng.shuffle(ids)
        n_dev = max(1, min(len(ids) - 1, round(len(ids) * dev_fraction)))
        dev.extend(ids[:n_dev])
        test.extend(ids[n_dev:])

    return {"seed": seed, "dev": sorted(dev), "test": sorted(test)}


def load_split(path: str | Path = SPLIT_PATH) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def category_counts(
    scenarios: Iterable[dict[str, Any]], split: dict[str, Any]
) -> dict[str, dict[str, int]]:
    category_of = {str(scenario["id"]): str(scenario["category"]) for scenario in scenarios}
    dev = Counter(category_of[scenario_id] for scenario_id in split["dev"])
    test = Counter(category_of[scenario_id] for scenario_id in split["test"])
    return {
        category: {"dev": dev.get(category, 0), "test": test.get(category, 0)}
        for category in sorted(set(dev) | set(test))
    }


def validate_split(scenarios: Iterable[dict[str, Any]], split: dict[str, Any]) -> None:
    ids = [str(scenario["id"]) for scenario in scenarios]
    dev = list(split["dev"])
    test = list(split["test"])
    if split.get("seed") != SEED:
        raise ValueError(f"Split seed must be {SEED}, got {split.get('seed')!r}.")
    if len(dev) != len(set(dev)) or len(test) != len(set(test)):
        raise ValueError("Split contains duplicate ids.")
    if set(dev) & set(test):
        raise ValueError(f"Split is not disjoint: {sorted(set(dev) & set(test))}")
    if set(dev) | set(test) != set(ids):
        missing = sorted(set(ids) - (set(dev) | set(test)))
        extra = sorted((set(dev) | set(test)) - set(ids))
        raise ValueError(f"Split does not cover the dataset. missing={missing} extra={extra}")
    counts = category_counts(scenarios, split)
    empty = [category for category, value in counts.items() if not value["dev"] or not value["test"]]
    if empty:
        raise ValueError(f"Categories without both splits: {empty}")


def _print_counts(scenarios: list[dict[str, Any]], split: dict[str, Any]) -> None:
    counts = category_counts(scenarios, split)
    print(f"seed={split['seed']} dev={len(split['dev'])} test={len(split['test'])}")
    print("| category | dev | test | total |")
    print("|---|---:|---:|---:|")
    for category, value in counts.items():
        print(f"| {category} | {value['dev']} | {value['test']} | {value['dev'] + value['test']} |")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build or verify the deterministic dev/test split.")
    parser.add_argument("--check", action="store_true", help="Verify eval/split.json without rewriting it.")
    parser.add_argument("--out", default=str(SPLIT_PATH), help="Output path for the split JSON.")
    args = parser.parse_args(argv)

    scenarios = load_scenarios()
    if args.check:
        split = load_split(args.out)
    else:
        split = build_split(scenarios)
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(split, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {args.out}")

    validate_split(scenarios, split)
    _print_counts(scenarios, split)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
