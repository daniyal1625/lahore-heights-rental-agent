"""The checked-in dev/test split is deterministic, disjoint and complete."""

from __future__ import annotations

from src.eval.split import (
    SPLIT_PATH,
    build_split,
    category_counts,
    load_scenarios,
    load_split,
    validate_split,
)


def test_split_is_disjoint_and_covers_every_scenario() -> None:
    scenarios = load_scenarios()
    split = load_split(SPLIT_PATH)
    validate_split(scenarios, split)

    ids = {str(scenario["id"]) for scenario in scenarios}
    assert len(scenarios) == 87
    assert set(split["dev"]).isdisjoint(split["test"])
    assert set(split["dev"]) | set(split["test"]) == ids
    assert len(split["dev"]) + len(split["test"]) == len(ids)


def test_split_is_stratified_and_reproducible() -> None:
    scenarios = load_scenarios()
    split = load_split(SPLIT_PATH)

    counts = category_counts(scenarios, split)
    assert counts
    assert all(value["dev"] >= 1 and value["test"] >= 1 for value in counts.values())
    assert build_split(scenarios) == split


def test_split_seed_is_42() -> None:
    assert load_split(SPLIT_PATH)["seed"] == 42
