"""Runner, RunResult and prompt tests. No LLM is involved."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from src.agent.prompts import ADDITIONS, BASE_SYSTEM_PROMPT, build_system_prompt
from src.agent.runner import (
    load_scenarios,
    model_tag,
    result_path,
    run_batch,
    select_scenarios,
)
from src.agent.systems import RunResult, format_reply


def test_run_result_is_json_serialisable() -> None:
    result = RunResult(
        system="rag",
        model="qwen2.5:3b",
        answer="Check-in is from 2:00 PM.",
        scenario_id="M-01",
        sources=[{"type": "manual", "id": "3.5"}],
        retrieved=["3.5"],
        tool_calls=[],
        latency_s=1.25,
        llm_s=1.0,
        retrieval_s=0.2,
        n_llm_calls=1,
        prompt_tokens=100,
        completion_tokens=20,
    )
    payload = json.loads(json.dumps(result.to_dict()))
    assert payload["system"] == "rag"
    assert payload["scenario_id"] == "M-01"
    assert payload["sources"] == [{"type": "manual", "id": "3.5"}]
    assert payload["prompt_tokens"] == 100


def test_format_reply_has_a_deterministic_sources_footer() -> None:
    result = RunResult(
        answer="Hello!",
        sources=[
            {"type": "manual", "id": "3.6"},
            {"type": "guide", "id": "Lahore > See"},
        ],
    )
    reply = format_reply(result)
    assert reply.startswith("Hello!")
    assert "Sources:" in reply
    assert "- manual 3.6" in reply
    assert "- guide Lahore > See" in reply

    empty = format_reply(RunResult(answer="Hi"))
    assert empty.rstrip().endswith("- none")


def test_shared_prompt_is_identical_and_additions_differ() -> None:
    prompts = {
        system: build_system_prompt(
            system, now="2026-11-10T10:00:00+05:00", guest_name="Sara Khan", reservation_id=90001
        )
        for system in ADDITIONS
    }
    for system, prompt in prompts.items():
        assert "Lahore Heights Apartments" in prompt
        assert "Sara Khan" in prompt
        assert "90001" in prompt
        assert prompt.startswith(BASE_SYSTEM_PROMPT.split("{now}")[0])
        assert prompt.endswith(ADDITIONS[system])

    # Every variant shares the base prompt and has its own distinct addition.
    assert len({prompt.split("\n\n")[-1] for prompt in prompts.values()}) == len(ADDITIONS)
    with pytest.raises(ValueError):
        build_system_prompt("nope", now="x", guest_name=None, reservation_id=None)


def test_model_tag_and_result_path() -> None:
    assert model_tag("qwen2.5:3b") == "qwen2.5-3b"
    path = result_path("results/runs", "qwen2.5:3b", "agent", "A-01")
    assert path == Path("results/runs/qwen2.5-3b/agent_v1/A-01.json")
    explicit = result_path("results/runs", "qwen2.5:3b", "agent_v1", "A-01")
    assert explicit == path
    assert result_path("results/runs", "qwen2.5:3b", "llm", "A-01") == Path(
        "results/runs/qwen2.5-3b/llm/A-01.json"
    )


def test_select_scenarios_by_ids_category_and_all() -> None:
    scenarios = load_scenarios()
    by_ids = select_scenarios(scenarios, ids=["M-01", "A-01"])
    assert [scenario["id"] for scenario in by_ids] == ["M-01", "A-01"]

    availability = select_scenarios(scenarios, category="availability_only")
    assert availability
    assert all(scenario["category"] == "availability_only" for scenario in availability)

    assert len(select_scenarios(scenarios, all_=True)) == len(scenarios)
    with pytest.raises(ValueError, match="Unknown scenario ids"):
        select_scenarios(scenarios, ids=["NOPE"])


def test_run_batch_writes_then_skips_then_forces(tmp_path: Path) -> None:
    scenarios = [
        {
            "id": "M-01",
            "guest_message": "hello",
            "thread_context": {"reservation_id": None, "guest_name": None},
        }
    ]
    systems = ["llm", "rag"]
    calls: list[tuple[str, str]] = []

    async def fake_run(system, message, thread_context, model=None):
        calls.append((system, message))
        return RunResult(system=system, model=model or "", answer=f"{system}: {message}")

    messages: list[str] = []
    first = asyncio.run(
        run_batch(
            scenarios,
            systems,
            model="fake:1b",
            out_dir=tmp_path,
            progress=messages.append,
            run_fn=fake_run,
        )
    )
    assert first["completed"] == 2
    assert first["skipped"] == 0
    assert len(calls) == 2

    for system in systems:
        path = result_path(tmp_path, "fake:1b", system, "M-01")
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["scenario_id"] == "M-01"
        assert payload["answer"].startswith(system)

    second = asyncio.run(
        run_batch(
            scenarios,
            systems,
            model="fake:1b",
            out_dir=tmp_path,
            progress=messages.append,
            run_fn=fake_run,
        )
    )
    assert second["completed"] == 0
    assert second["skipped"] == 2
    assert len(calls) == 2
    assert any(message.startswith("[skip]") for message in messages)

    third = asyncio.run(
        run_batch(
            scenarios,
            systems,
            model="fake:1b",
            out_dir=tmp_path,
            force=True,
            progress=messages.append,
            run_fn=fake_run,
        )
    )
    assert third["completed"] == 2
    assert len(calls) == 4
