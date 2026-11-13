"""Tool tests against the in-process mock API. No LLM is involved."""

from __future__ import annotations

import asyncio
import json

import pytest

from src.agent.tools import (
    check_availability,
    dedupe_sources,
    get_reservation,
    reset_api_client,
    search_house_manual,
    search_local_guide,
    sources_from_tool_result,
)

try:
    from src.rag.index import index_exists

    _INDEX_AVAILABLE = index_exists()
except Exception:  # pragma: no cover - optional RAG dependency missing
    _INDEX_AVAILABLE = False

requires_index = pytest.mark.skipif(
    not _INDEX_AVAILABLE,
    reason="Chroma index missing; run `python -m src.rag build` first.",
)


def _call(tool, args: dict) -> dict:
    payload = asyncio.run(tool.ainvoke(args))
    return json.loads(payload)


@pytest.fixture(autouse=True)
def fresh_api_client(seeded_db):
    reset_api_client()
    yield
    reset_api_client()


def test_check_availability_returns_expected_listings(seeded_db) -> None:
    payload = _call(
        check_availability,
        {"check_in": "2026-11-12", "check_out": "2026-11-14", "guests": 2},
    )

    assert payload["check_in"] == "2026-11-12"
    assert payload["check_out"] == "2026-11-14"
    assert payload["nights"] == 2
    assert payload["guests"] == 2
    available = {item["listing_id"] for item in payload["results"] if item["available"]}
    assert available == {1001, 1003, 1004}
    studio = next(item for item in payload["results"] if item["listing_id"] == 1001)
    assert studio["nightly_price_pkr"] == 9500
    assert studio["stay_total_pkr"] == 19000
    assert "extra guest fee" in payload["note"]


def test_check_availability_rejects_invalid_range(seeded_db) -> None:
    payload = _call(
        check_availability,
        {"check_in": "2026-11-14", "check_out": "2026-11-12"},
    )
    assert "error" in payload
    assert "after" in payload["error"].lower()


def test_check_availability_rejects_past_dates(seeded_db) -> None:
    payload = _call(
        check_availability,
        {"check_in": "2026-11-01", "check_out": "2026-11-03"},
    )
    assert "error" in payload
    assert "past" in payload["error"].lower()


def test_get_reservation_maps_fixture_fields(seeded_db) -> None:
    payload = _call(get_reservation, {"reservation_id": 90004})
    assert payload["id"] == 90004
    assert payload["guest_name"] == "Hamza Sheikh"
    assert payload["listing"] == "Penthouse, Unit 701"
    assert payload["arrival"] == "2026-11-20"
    assert payload["departure"] == "2026-11-24"
    assert payload["nights"] == 4
    assert payload["check_in_time"] == "2:00 PM"
    assert payload["check_out_time"] == "11:00 AM"
    assert payload["balance_due_pkr"] == 76000
    assert payload["balance_due_date"] == "2026-11-18"
    assert payload["security_deposit_status"] == "pending"
    assert payload["id_verification"] == "pending"


def test_get_reservation_not_found_is_an_error_json(seeded_db) -> None:
    payload = _call(get_reservation, {"reservation_id": 99999})
    assert payload == {"error": "Reservation 99999 not found"}


@requires_index
def test_manual_search_returns_section_source_ids(seeded_db) -> None:
    payload = _call(search_house_manual, {"query": "late checkout"})
    assert payload
    assert {"source_id", "title", "text"} <= set(payload[0])
    assert any(item["source_id"] == "14.3" for item in payload)


@requires_index
def test_guide_search_returns_heading_path_source_ids(seeded_db) -> None:
    payload = _call(search_local_guide, {"query": "Badshahi Mosque opening hours"})
    assert payload
    assert any(item["source_id"] == "Lahore > See > Walled City" for item in payload)


def test_sources_from_tool_results_are_deterministic() -> None:
    manual = json.dumps([{"source_id": "3.6", "title": "x", "text": "y"}])
    guide = json.dumps([{"source_id": "Lahore > See", "title": "x", "text": "y"}])
    reservation = json.dumps({"id": 90004})
    availability = json.dumps({"check_in": "2026-11-12", "check_out": "2026-11-14"})

    assert sources_from_tool_result("search_house_manual", manual) == [
        {"type": "manual", "id": "3.6"}
    ]
    assert sources_from_tool_result("search_local_guide", guide) == [
        {"type": "guide", "id": "Lahore > See"}
    ]
    assert sources_from_tool_result("get_reservation", reservation) == [
        {"type": "reservation", "id": "90004"}
    ]
    assert sources_from_tool_result("check_availability", availability) == [
        {"type": "availability", "id": "2026-11-12..2026-11-14"}
    ]
    assert sources_from_tool_result("get_reservation", '{"error":"nope"}') == []


def test_dedupe_sources_preserves_first_occurrence() -> None:
    sources = [
        {"type": "manual", "id": "3.6"},
        {"type": "guide", "id": "Lahore"},
        {"type": "manual", "id": "3.6"},
    ]
    assert dedupe_sources(sources) == [
        {"type": "manual", "id": "3.6"},
        {"type": "guide", "id": "Lahore"},
    ]
