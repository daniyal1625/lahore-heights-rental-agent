"""Fast tests for the Stage 5 guards (no model calls)."""

from __future__ import annotations

import asyncio
import json

from src.agent.guards import (
    NOT_AUTHORIZED,
    date_helper,
    guarded_get_reservation,
    names_match,
    reservation_access_allowed,
)


def _fetch_returning(payload: dict, calls: list[dict] | None = None):
    async def fetch(args: dict) -> str:
        if calls is not None:
            calls.append(args)
        return json.dumps(payload)

    return fetch


def test_own_booking_is_allowed() -> None:
    calls: list[dict] = []
    content = asyncio.run(
        guarded_get_reservation(
            90002,
            {"reservation_id": 90002, "guest_name": "Omar Farooq"},
            fetch=_fetch_returning({"id": 90002, "guest_name": "Omar Farooq"}, calls),
        )
    )
    assert json.loads(content)["id"] == 90002
    assert calls == [{"reservation_id": 90002}]


def test_other_booking_is_denied_without_fetching() -> None:
    calls: list[dict] = []
    content = asyncio.run(
        guarded_get_reservation(
            90002,
            {"reservation_id": 90001, "guest_name": "Sara Khan"},
            fetch=_fetch_returning({"id": 90002, "guest_name": "Omar Farooq"}, calls),
        )
    )
    assert json.loads(content) == NOT_AUTHORIZED
    assert calls == []


def test_name_match_when_thread_id_is_null() -> None:
    content = asyncio.run(
        guarded_get_reservation(
            90003,
            {"reservation_id": None, "guest_name": "Emily Carter"},
            fetch=_fetch_returning({"id": 90003, "guest_name": "emily carter"}),
        )
    )
    assert json.loads(content)["id"] == 90003


def test_wrong_name_is_denied_when_thread_id_is_null() -> None:
    content = asyncio.run(
        guarded_get_reservation(
            90003,
            {"reservation_id": None, "guest_name": "Emily Carter"},
            fetch=_fetch_returning({"id": 90003, "guest_name": "Omar Farooq"}),
        )
    )
    assert json.loads(content) == NOT_AUTHORIZED


def test_name_matching_uses_first_and_last_token() -> None:
    assert names_match("Sara  Khan", "sara khan") is True
    assert names_match("Sara Khan", "Sara Ali") is False
    assert names_match(None, "Sara Khan") is False


def test_access_rule_helper() -> None:
    assert reservation_access_allowed(90001, {"reservation_id": 90001}) is True
    assert reservation_access_allowed(90002, {"reservation_id": 90001}) is False
    assert (
        reservation_access_allowed(
            90003, {"reservation_id": None, "guest_name": "Emily Carter"}, "Emily Carter"
        )
        is True
    )
    assert (
        reservation_access_allowed(
            90003, {"reservation_id": None, "guest_name": "Emily Carter"}, "Omar Farooq"
        )
        is False
    )


def test_date_helper_has_today_tomorrow_and_rule() -> None:
    text = date_helper("2026-11-10T10:00:00+05:00")
    assert "Tuesday 10 November 2026" in text
    assert "(2026-11-10)" in text
    assert "Tomorrow is Wednesday 11 November 2026" in text
    assert "(2026-11-11)" in text
    assert "YYYY-MM-DD" in text
