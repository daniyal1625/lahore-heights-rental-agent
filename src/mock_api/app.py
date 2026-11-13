"""FastAPI mock of a small Hostaway-style surface, plus one local availability route.

GET /v1/availability is not part of the real Hostaway API. It is a convenience
route for this portfolio project. Every other /v1 route follows the field names
and the {"status": "success", "result": ...} envelope used by the fixtures.

The simulated date comes from SIMULATED_NOW. This module does not read the real clock.
"""

from __future__ import annotations

import hmac
import json
import sqlite3
import urllib.parse
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, timedelta
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from mock_api import __version__
from mock_api.db import connect
from mock_api.rules import ranges_overlap, stay_total
from mock_api.settings import ACCESS_TOKEN, database_path, simulated_now, simulated_today

ATTRIBUTION = (
    'Local guide snapshot: English Wikivoyage article "Lahore" '
    "(https://en.wikivoyage.org/wiki/Lahore), revision 5410746, retrieved 2026-11-10, "
    "Creative Commons Attribution-ShareAlike 4.0. Attributed to the Wikivoyage contributors. "
    "See data/local_guide/SOURCE.md."
)

DESCRIPTION = """
Local mock API for the fictional Lahore Heights Apartments (Gulberg III, Lahore).

The simulated "today" is the SIMULATED_NOW environment variable
(default 2026-11-10T10:00:00+05:00). The process clock is not used.

**Not a Hostaway endpoint:** `GET /v1/availability` is a project convenience route.
It quotes every listing for a stay. Real Hostaway clients should use the listings,
calendar, and reservations routes.

A night is occupied when arrival <= night < departure. A departure morning may be
a new arrival (same-day turnover). Cancelled reservations do not block the calendar.
ownerStay does. A party larger than personCapacity is not available.

""" + ATTRIBUTION


class ApiError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message


def create_app() -> FastAPI:
    app = FastAPI(
        title="Lahore Heights mock API",
        version=__version__,
        description=DESCRIPTION,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.exception_handler(ApiError)
    def _api_error(_request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"status": "fail", "message": exc.message})

    @app.exception_handler(RequestValidationError)
    def _validation_error(_request: Request, exc: RequestValidationError) -> JSONResponse:
        parts = []
        for error in exc.errors():
            loc = ".".join(str(item) for item in error.get("loc", []) if item not in ("query", "body", "path"))
            parts.append(f"{loc}: {error.get('msg')}" if loc else str(error.get("msg")))
        message = "; ".join(parts) or "Invalid request."
        return JSONResponse(status_code=422, content={"status": "fail", "message": message})

    @app.get("/health")
    def health(_token: Annotated[None, Depends(require_token)]) -> dict[str, Any]:
        now = simulated_now()
        return {"status": "success", "result": {"ok": True, "simulatedNow": now.isoformat()}}

    @app.get("/openapi.json", include_in_schema=False)
    def openapi_schema(_token: Annotated[None, Depends(require_token)]) -> dict[str, Any]:
        return app.openapi()

    @app.get("/")
    def root(_token: Annotated[None, Depends(require_token)]) -> dict[str, Any]:
        return {
            "status": "success",
            "result": {
                "service": "Lahore Heights mock API",
                "simulatedNow": simulated_now().isoformat(),
                "health": "/health",
                "openapi": "/openapi.json",
                "customEndpoints": ["/v1/availability"],
                "attribution": ATTRIBUTION,
            },
        }

    @app.post("/v1/accessTokens")
    async def access_tokens(request: Request) -> dict[str, Any]:
        body = await _read_credentials(request)
        grant = body.get("grant_type")
        if grant != "client_credentials":
            raise ApiError(400, "grant_type must be client_credentials.")
        if not str(body.get("client_id") or "").strip() or not str(body.get("client_secret") or "").strip():
            raise ApiError(400, "client_id and client_secret are required.")
        return {
            "status": "success",
            "result": {
                "token_type": "Bearer",
                "expires_in": 31536000,
                "access_token": ACCESS_TOKEN,
            },
        }

    @app.get("/v1/listings")
    def list_listings(_token: Annotated[None, Depends(require_token)]) -> dict[str, Any]:
        with _db() as conn:
            return {"status": "success", "result": _listings(conn)}

    @app.get("/v1/listings/{listing_id}")
    def get_listing(listing_id: int, _token: Annotated[None, Depends(require_token)]) -> dict[str, Any]:
        with _db() as conn:
            listing = _listing(conn, listing_id)
            return {"status": "success", "result": listing}

    @app.get("/v1/listings/{listing_id}/calendar")
    def listing_calendar(
        listing_id: int,
        startDate: str,
        endDate: str,
        _token: Annotated[None, Depends(require_token)],
    ) -> dict[str, Any]:
        start = _parse_date(startDate, "startDate")
        end = _parse_date(endDate, "endDate")
        if end < start:
            raise ApiError(400, "endDate must be on or after startDate. Each date is one night.")
        with _db() as conn:
            listing = _listing(conn, listing_id)
            reservations = _reservations(conn, listing_id)
        days = []
        day = start
        while day <= end:
            blocking = [row for row in reservations if _blocks_night(row, day)]
            if not blocking:
                available, status = True, "available"
            elif any(row["status"] == "ownerStay" for row in blocking):
                available, status = False, "blocked"
            else:
                available, status = False, "reserved"
            days.append(
                {
                    "date": day.isoformat(),
                    "isAvailable": available,
                    "price": listing["price"],
                    "status": status,
                }
            )
            day += timedelta(days=1)
        return {"status": "success", "result": days}

    @app.get("/v1/reservations/{reservation_id}")
    def get_reservation(reservation_id: int, _token: Annotated[None, Depends(require_token)]) -> dict[str, Any]:
        with _db() as conn:
            row = _reservation(conn, reservation_id)
            return {"status": "success", "result": row}

    @app.get("/v1/reservations")
    def list_reservations(
        _token: Annotated[None, Depends(require_token)],
        listingId: int | None = None,
        arrivalStartDate: str | None = None,
        arrivalEndDate: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        if limit < 1 or limit > 1000:
            raise ApiError(400, "limit must be between 1 and 1000.")
        if offset < 0:
            raise ApiError(400, "offset must be 0 or greater.")
        arrival_start = _parse_date(arrivalStartDate, "arrivalStartDate") if arrivalStartDate else None
        arrival_end = _parse_date(arrivalEndDate, "arrivalEndDate") if arrivalEndDate else None
        if arrival_start and arrival_end and arrival_end < arrival_start:
            raise ApiError(400, "arrivalEndDate must be on or after arrivalStartDate.")
        clauses: list[str] = []
        params: list[Any] = []
        with _db() as conn:
            if listingId is not None:
                _listing(conn, listingId)
                clauses.append("listing_map_id = ?")
                params.append(listingId)
            if arrival_start is not None:
                clauses.append("arrival_date >= ?")
                params.append(arrival_start.isoformat())
            if arrival_end is not None:
                clauses.append("arrival_date <= ?")
                params.append(arrival_end.isoformat())
            where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
            total = conn.execute(f"SELECT COUNT(*) AS n FROM reservations{where}", params).fetchone()["n"]
            rows = conn.execute(
                f"SELECT payload FROM reservations{where} ORDER BY arrival_date, id LIMIT ? OFFSET ?",
                [*params, limit, offset],
            ).fetchall()
        return {
            "status": "success",
            "result": [json.loads(row["payload"]) for row in rows],
            "count": total,
            "limit": limit,
            "offset": offset,
        }

    @app.get("/v1/availability")
    def availability(
        checkIn: str,
        checkOut: str,
        _token: Annotated[None, Depends(require_token)],
        guests: Annotated[int | None, Query()] = None,
    ) -> dict[str, Any]:
        """Project-only quote. Not part of the real Hostaway API."""
        check_in = _parse_date(checkIn, "checkIn")
        check_out = _parse_date(checkOut, "checkOut")
        today = simulated_today()
        if check_in < today:
            raise ApiError(
                400,
                f"checkIn {check_in.isoformat()} is in the past relative to the simulated date {today.isoformat()}.",
            )
        if check_out <= check_in:
            raise ApiError(400, "checkOut must be after checkIn. Nights are checkIn inclusive through checkOut exclusive.")
        if guests is not None and guests < 1:
            raise ApiError(400, "guests must be 1 or greater when it is provided. Omit guests if the party size is unknown.")
        nights = (check_out - check_in).days
        with _db() as conn:
            listings = _listings(conn)
            reservations = _reservations(conn)
        quotes = []
        for listing in listings:
            over_capacity = guests is not None and guests > int(listing["personCapacity"])
            busy = any(
                row["listingMapId"] == listing["id"] and _blocks_stay(row, check_in, check_out) for row in reservations
            )
            quotes.append(
                {
                    "listingId": listing["id"],
                    "name": listing["name"],
                    "available": not over_capacity and not busy,
                    "nightlyPrice": listing["price"],
                    "nights": nights,
                    "stayTotal": stay_total(listing, guests, nights),
                    "personCapacity": listing["personCapacity"],
                    "guestsIncluded": listing["guestsIncluded"],
                    "currency": listing["currencyCode"],
                }
            )
        return {"status": "success", "result": quotes}

    return app


def require_token(authorization: Annotated[str | None, Header()] = None) -> None:
    if not authorization:
        raise ApiError(401, "Missing Authorization header. Expected: Bearer <token>.")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise ApiError(401, "Invalid Authorization header. Expected: Bearer <token>.")
    if not hmac.compare_digest(token.strip(), ACCESS_TOKEN):
        raise ApiError(401, "Invalid access token.")


async def _read_credentials(request: Request) -> dict[str, Any]:
    raw = await request.body()
    if not raw.strip():
        raise ApiError(400, "Request body is required. Send grant_type, client_id, and client_secret.")
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type or raw.lstrip().startswith(b"{"):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ApiError(400, "Request body is not valid JSON.") from exc
        if not isinstance(data, dict):
            raise ApiError(400, "JSON body must be an object.")
        return data
    pairs = urllib.parse.parse_qsl(raw.decode("utf-8"), keep_blank_values=True)
    if not pairs:
        raise ApiError(400, "Could not read client_credentials. Send JSON or application/x-www-form-urlencoded.")
    return dict(pairs)


def _parse_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ApiError(400, f"{field} must be a date in YYYY-MM-DD format.") from exc


def _blocks_night(reservation: dict, night: date) -> bool:
    if reservation["status"] == "cancelled":
        return False
    arrival = date.fromisoformat(reservation["arrivalDate"])
    departure = date.fromisoformat(reservation["departureDate"])
    return arrival <= night < departure


def _blocks_stay(reservation: dict, check_in: date, check_out: date) -> bool:
    if reservation["status"] == "cancelled":
        return False
    arrival = date.fromisoformat(reservation["arrivalDate"])
    departure = date.fromisoformat(reservation["departureDate"])
    return ranges_overlap(arrival, departure, check_in, check_out)


@contextmanager
def _db() -> Iterator[sqlite3.Connection]:
    conn = connect(database_path())
    try:
        try:
            conn.execute("SELECT 1 FROM listings LIMIT 1").fetchone()
        except sqlite3.OperationalError as exc:
            raise ApiError(500, "Database is not seeded. Run python -m mock_api.seed.") from exc
        yield conn
    finally:
        conn.close()


def _listings(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT payload FROM listings ORDER BY id").fetchall()
    return [json.loads(row["payload"]) for row in rows]


def _listing(conn: sqlite3.Connection, listing_id: int) -> dict:
    row = conn.execute("SELECT payload FROM listings WHERE id = ?", (listing_id,)).fetchone()
    if row is None:
        raise ApiError(404, f"Listing {listing_id} not found.")
    return json.loads(row["payload"])


def _reservations(conn: sqlite3.Connection, listing_id: int | None = None) -> list[dict]:
    if listing_id is None:
        rows = conn.execute("SELECT payload FROM reservations").fetchall()
    else:
        rows = conn.execute(
            "SELECT payload FROM reservations WHERE listing_map_id = ?",
            (listing_id,),
        ).fetchall()
    return [json.loads(row["payload"]) for row in rows]


def _reservation(conn: sqlite3.Connection, reservation_id: int) -> dict:
    row = conn.execute("SELECT payload FROM reservations WHERE id = ?", (reservation_id,)).fetchone()
    if row is None:
        raise ApiError(404, f"Reservation {reservation_id} not found.")
    return json.loads(row["payload"])


app = create_app()
