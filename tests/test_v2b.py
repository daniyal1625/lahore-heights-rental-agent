"""Fast tests for the Stage 5 planner-executor pieces (no model calls)."""

from __future__ import annotations

import asyncio
import json

from src.agent import systems
from src.agent.systems import (
    PLAN_SCHEMA,
    PLAN_TOOL_NAMES,
    RunResult,
    _call_planner,
    coerce_plan,
    execute_plan,
    fallback_plan,
)


class FakeResponse:
    def __init__(self, content: str) -> None:
        self.content = content
        self.response_metadata: dict = {}
        self.usage_metadata: dict = {}


class FakePlanner:
    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.calls = 0

    async def ainvoke(self, messages):  # noqa: ANN001 - mimics ChatOllama
        content = self.replies[min(self.calls, len(self.replies) - 1)]
        self.calls += 1
        return FakeResponse(content)


class FakeTool:
    def __init__(self, payload: str) -> None:
        self.payload = payload
        self.calls: list[dict] = []

    async def ainvoke(self, args):  # noqa: ANN001 - mimics a LangChain tool
        self.calls.append(args)
        return self.payload


def _call(tool: str, **overrides) -> dict:
    call = {
        "tool": tool,
        "query": None,
        "reservation_id": None,
        "check_in": None,
        "check_out": None,
        "guests": None,
    }
    call.update(overrides)
    return call


def test_plan_schema_is_intent_plus_calls() -> None:
    assert set(PLAN_SCHEMA["properties"]) == {"intent", "calls"}
    assert set(PLAN_SCHEMA["required"]) == {"intent", "calls"}
    item = PLAN_SCHEMA["properties"]["calls"]["items"]
    assert item["properties"]["tool"]["enum"] == list(PLAN_TOOL_NAMES)
    assert "tool" in item["required"]


def test_planner_json_falls_back_after_two_failures() -> None:
    result = RunResult()
    planner = FakePlanner(["not json", "still not json"])
    plan, error = asyncio.run(
        _call_planner(planner, [], result, "What is the wifi password?")
    )
    assert planner.calls == 2
    assert result.plan_attempts == 2
    assert plan == fallback_plan("What is the wifi password?")
    assert plan["calls"][0]["tool"] == "search_house_manual"
    assert plan["calls"][0]["query"] == "What is the wifi password?"
    assert error


def test_planner_retries_once_then_succeeds() -> None:
    valid = json.dumps(
        {
            "intent": "wifi",
            "calls": [_call("search_house_manual", query="wifi password")],
        }
    )
    result = RunResult()
    planner = FakePlanner(["oops", valid])
    plan, error = asyncio.run(_call_planner(planner, [], result, "wifi?"))
    assert planner.calls == 2
    assert result.plan_attempts == 2
    assert plan["calls"][0]["query"] == "wifi password"
    assert error is None


def test_coerce_plan_normalises_types_and_drops_unknown_tools() -> None:
    plan = coerce_plan(
        {
            "intent": "booking",
            "calls": [
                _call("get_reservation", reservation_id="90002"),
                _call("not_a_tool", query="nope"),
                _call("search_house_manual", query="N/A"),
            ],
        }
    )
    assert plan is not None
    assert [call["tool"] for call in plan["calls"]] == ["get_reservation", "search_house_manual"]
    assert plan["calls"][0]["reservation_id"] == 90002
    assert plan["calls"][1]["query"] is None


def test_coerce_plan_requires_the_calls_array() -> None:
    assert coerce_plan({"intent": "wifi"}) is None
    assert coerce_plan({"intent": "wifi", "calls": "search_house_manual"}) is None
    assert coerce_plan({"intent": "greeting", "calls": []}) == {"intent": "greeting", "calls": []}


def test_execute_plan_skips_availability_without_dates() -> None:
    plan = coerce_plan({"intent": "dates", "calls": [_call("check_availability")]})
    outcome = asyncio.run(execute_plan(plan, {}))
    assert outcome["tool_calls"] == []
    assert outcome["needs_clarification"] is True


def test_execute_plan_runs_selected_tools_and_records_sources(monkeypatch) -> None:
    payload = json.dumps(
        [{"source_id": "4.1", "title": "Wifi", "text": "The wifi code is on the router."}]
    )
    fake = FakeTool(payload)
    monkeypatch.setitem(systems.TOOLS_BY_NAME, "search_house_manual", fake)
    plan = coerce_plan(
        {
            "intent": "wifi",
            "calls": [_call("search_house_manual", query="wifi code")],
        }
    )
    outcome = asyncio.run(execute_plan(plan, {}))
    assert fake.calls == [{"query": "wifi code"}]
    assert [call["name"] for call in outcome["tool_calls"]] == ["search_house_manual"]
    assert outcome["sources"] == [{"type": "manual", "id": "4.1"}]
    assert outcome["needs_clarification"] is False
    assert outcome["used_fallback"] is False


def test_execute_plan_uses_thread_reservation_and_guard(monkeypatch) -> None:
    captured: list[tuple] = []

    async def fake_guard(reservation_id, thread_context):  # noqa: ANN001
        captured.append((reservation_id, thread_context))
        return json.dumps({"id": reservation_id, "guest_name": "Omar Farooq"})

    monkeypatch.setattr(systems, "guarded_get_reservation", fake_guard)
    plan = coerce_plan(
        {"intent": "booking", "calls": [_call("get_reservation")]}
    )
    outcome = asyncio.run(
        execute_plan(plan, {"reservation_id": 90002, "guest_name": "Omar Farooq"})
    )
    assert captured == [(90002, {"reservation_id": 90002, "guest_name": "Omar Farooq"})]
    assert [call["name"] for call in outcome["tool_calls"]] == ["get_reservation"]
    assert outcome["sources"] == [{"type": "reservation", "id": "90002"}]


def test_execute_plan_falls_back_to_manual_for_a_question(monkeypatch) -> None:
    fake = FakeTool(json.dumps([{"source_id": "18.1", "title": "FAQ", "text": "Check-in is 2 PM."}]))
    monkeypatch.setitem(systems.TOOLS_BY_NAME, "search_house_manual", fake)
    plan = coerce_plan({"intent": "unclear", "calls": []})
    outcome = asyncio.run(
        execute_plan(plan, {}, "What time is check-in?")
    )
    assert outcome["used_fallback"] is True
    assert fake.calls == [{"query": "What time is check-in?"}]
    assert [call["name"] for call in outcome["tool_calls"]] == ["search_house_manual"]


def test_execute_plan_keeps_no_tools_for_a_greeting(monkeypatch) -> None:
    fake = FakeTool("[]")
    monkeypatch.setitem(systems.TOOLS_BY_NAME, "search_house_manual", fake)
    plan = coerce_plan({"intent": "greeting", "calls": []})
    outcome = asyncio.run(execute_plan(plan, {}, "Thanks so much!"))
    assert outcome["used_fallback"] is False
    assert outcome["tool_calls"] == []
    assert fake.calls == []
