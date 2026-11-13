import json
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROTECTED_START = date(2026, 11, 8)
PROTECTED_END_EXCLUSIVE = date(2027, 1, 1)


def _scenarios() -> list[dict]:
    return json.loads((ROOT / "eval" / "scenarios.json").read_text(encoding="utf-8"))["scenarios"]


def _availability_cases():
    cases = []
    for scenario in _scenarios():
        expected = scenario.get("expected_available_listing_ids")
        args = (scenario.get("expected_args") or {}).get("check_availability")
        if expected is not None and args:
            cases.append(pytest.param(args, expected, id=scenario["id"]))
    return cases


def _reservation_ids() -> list[int]:
    found = set()
    for scenario in _scenarios():
        args = (scenario.get("expected_args") or {}).get("get_reservation")
        if not args:
            continue
        reservation_id = args["reservation_id"]
        if reservation_id != 99999:
            found.add(reservation_id)
    return sorted(found)


def _ranges_overlap(start_a: date, end_a: date, start_b: date, end_b: date) -> bool:
    return start_a < end_b and start_b < end_a


@pytest.mark.parametrize(("args", "expected"), _availability_cases())
def test_scenario_availability(client, auth_header, args, expected):
    params = {"checkIn": args["check_in"], "checkOut": args["check_out"]}
    if args.get("guests") is not None:
        params["guests"] = args["guests"]
    response = client.get("/v1/availability", params=params, headers=auth_header)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "success"
    available = [row["listingId"] for row in body["result"] if row["available"]]
    assert available == expected


@pytest.mark.parametrize("reservation_id", _reservation_ids())
def test_scenario_reservations_exist(client, auth_header, reservation_id):
    response = client.get(f"/v1/reservations/{reservation_id}", headers=auth_header)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "success"
    assert body["result"]["id"] == reservation_id


def test_unknown_reservation_is_404(client, auth_header):
    response = client.get("/v1/reservations/99999", headers=auth_header)
    assert response.status_code == 404
    body = response.json()
    assert body["status"] == "fail"
    assert "99999" in body["message"]
    assert "not found" in body["message"].lower()


def test_fixture_reservations_round_trip(client, auth_header):
    fixtures = json.loads((ROOT / "data" / "fixtures" / "reservations_fixed.json").read_text(encoding="utf-8"))
    for reservation in fixtures["result"]:
        response = client.get(f"/v1/reservations/{reservation['id']}", headers=auth_header)
        assert response.status_code == 200, response.text
        assert response.json()["result"] == reservation


def test_fixture_listings_round_trip(client, auth_header):
    fixtures = json.loads((ROOT / "data" / "fixtures" / "listings.json").read_text(encoding="utf-8"))
    response = client.get("/v1/listings", headers=auth_header)
    assert response.status_code == 200
    assert response.json()["result"] == fixtures["result"]


def test_random_reservations_do_not_overlap_or_touch_protected_window(client, auth_header):
    fixtures = json.loads((ROOT / "data" / "fixtures" / "reservations_fixed.json").read_text(encoding="utf-8"))
    listings = {
        row["id"]: row
        for row in json.loads((ROOT / "data" / "fixtures" / "listings.json").read_text(encoding="utf-8"))["result"]
    }
    fixed_ids = {row["id"] for row in fixtures["result"]}
    response = client.get("/v1/reservations", params={"limit": 1000}, headers=auth_header)
    assert response.status_code == 200, response.text
    rows = response.json()["result"]
    random_rows = [row for row in rows if row["id"] not in fixed_ids]
    assert len(random_rows) == 150
    occupied: dict[int, list[tuple[date, date]]] = {listing_id: [] for listing_id in listings}
    countries = set()
    for row in random_rows:
        assert 10000 <= row["id"] <= 89999
        arrival = date.fromisoformat(row["arrivalDate"])
        departure = date.fromisoformat(row["departureDate"])
        assert not _ranges_overlap(arrival, departure, PROTECTED_START, PROTECTED_END_EXCLUSIVE)
        assert (departure - arrival).days == row["nights"]
        listing = listings[row["listingMapId"]]
        assert row["numberOfGuests"] <= listing["personCapacity"]
        if row["status"] == "ownerStay":
            assert row["totalPrice"] == 0
        else:
            extra = max(0, row["numberOfGuests"] - listing["guestsIncluded"]) * row["nights"] * listing["extraGuestFee"]
            assert row["totalPrice"] == row["nights"] * listing["price"] + extra
        for other_arrival, other_departure in occupied[row["listingMapId"]]:
            assert not _ranges_overlap(arrival, departure, other_arrival, other_departure)
        occupied[row["listingMapId"]].append((arrival, departure))
        countries.add(row["guestCountry"])
        assert row["guestName"].strip()
    assert "PK" in countries
    assert any(country != "PK" for country in countries)


def test_active_reservations_including_fixtures_do_not_overlap(client, auth_header):
    response = client.get("/v1/reservations", params={"limit": 1000}, headers=auth_header)
    active = [row for row in response.json()["result"] if row["status"] != "cancelled"]
    for index, row in enumerate(active):
        for other in active[index + 1 :]:
            if row["listingMapId"] != other["listingMapId"]:
                continue
            assert not _ranges_overlap(
                date.fromisoformat(row["arrivalDate"]),
                date.fromisoformat(row["departureDate"]),
                date.fromisoformat(other["arrivalDate"]),
                date.fromisoformat(other["departureDate"]),
            )


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/health",
        "/openapi.json",
        "/v1/listings",
        "/v1/listings/1001",
        "/v1/listings/1001/calendar?startDate=2026-11-12&endDate=2026-11-13",
        "/v1/reservations",
        "/v1/reservations/90001",
        "/v1/availability?checkIn=2026-11-12&checkOut=2026-11-14&guests=2",
    ],
)
def test_missing_token_is_401(client, path):
    response = client.get(path)
    assert response.status_code == 401
    assert response.json()["status"] == "fail"


def test_bad_token_is_401(client):
    response = client.get("/v1/listings", headers={"Authorization": "Bearer wrong-token"})
    assert response.status_code == 401
    assert response.json()["status"] == "fail"


def test_health_and_openapi_work_with_token(client, auth_header):
    health = client.get("/health", headers=auth_header)
    assert health.status_code == 200
    assert health.json()["result"]["ok"] is True
    schema = client.get("/openapi.json", headers=auth_header)
    assert schema.status_code == 200
    assert "/v1/availability" in schema.json()["paths"]


def test_demo_quote_nov_12_to_14(client, auth_header):
    response = client.get(
        "/v1/availability",
        params={"checkIn": "2026-11-12", "checkOut": "2026-11-14", "guests": 2},
        headers=auth_header,
    )
    assert response.status_code == 200
    rows = {row["listingId"]: row for row in response.json()["result"]}
    assert [row["listingId"] for row in response.json()["result"] if row["available"]] == [1001, 1003, 1004]
    assert rows[1001]["stayTotal"] == 19000
    assert rows[1001]["nights"] == 2
    assert rows[1001]["nightlyPrice"] == 9500
    assert rows[1003]["stayTotal"] == 42000
    assert rows[1004]["stayTotal"] == 76000
    assert rows[1002]["available"] is False


def test_extra_guest_fee_is_included(client, auth_header):
    response = client.get(
        "/v1/availability",
        params={"checkIn": "2026-12-06", "checkOut": "2026-12-08", "guests": 3},
        headers=auth_header,
    )
    assert response.status_code == 200
    one_bedroom = next(row for row in response.json()["result"] if row["listingId"] == 1002)
    assert one_bedroom["available"] is True
    assert one_bedroom["guestsIncluded"] == 2
    assert one_bedroom["stayTotal"] == 32000


def test_past_check_in_is_400(client, auth_header):
    response = client.get(
        "/v1/availability",
        params={"checkIn": "2026-11-05", "checkOut": "2026-11-07", "guests": 2},
        headers=auth_header,
    )
    assert response.status_code == 400
    body = response.json()
    assert body["status"] == "fail"
    assert "2026-11-05" in body["message"]
    assert "2026-11-10" in body["message"]
    assert "past" in body["message"].lower()


def test_cancelled_night_is_available_on_the_calendar(client, auth_header):
    response = client.get(
        "/v1/listings/1001/calendar",
        params={"startDate": "2026-11-25", "endDate": "2026-11-26"},
        headers=auth_header,
    )
    assert response.status_code == 200
    days = response.json()["result"]
    assert [(day["date"], day["isAvailable"], day["status"], day["price"]) for day in days] == [
        ("2026-11-25", True, "available", 9500),
        ("2026-11-26", True, "available", 9500),
    ]


def test_owner_stay_blocks_the_calendar(client, auth_header):
    response = client.get(
        "/v1/listings/1003/calendar",
        params={"startDate": "2026-11-28", "endDate": "2026-11-28"},
        headers=auth_header,
    )
    assert response.status_code == 200
    day = response.json()["result"][0]
    assert day["isAvailable"] is False
    assert day["status"] == "blocked"


def test_token_accepts_form_body(client):
    response = client.post(
        "/v1/accessTokens",
        data={"grant_type": "client_credentials", "client_id": "lahore-heights", "client_secret": "local-dev"},
    )
    assert response.status_code == 200
    assert response.json()["result"]["token_type"] == "Bearer"
    assert response.json()["result"]["access_token"]
