"""LangChain tools for the tool-using guest-messaging agent.

The API client talks to the FastAPI mock in-process through
``httpx.ASGITransport`` by default. Setting ``MOCK_API_URL`` switches to real
HTTP without any other code change. The bearer token is fetched once from
``POST /v1/accessTokens`` and reused.

Tools never raise into the model: HTTP, validation and unexpected errors are
returned as ``{"error": "..."}`` JSON. Each call is logged with its name,
arguments, duration and result size.
"""

from __future__ import annotations

import asyncio
import json
import logging
from time import perf_counter
from typing import Any

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.config import (
    MOCK_API_URL,
    MOCK_CLIENT_ID,
    MOCK_CLIENT_SECRET,
    RAG_MODE,
    REQUEST_TIMEOUT_S,
    TOOL_SEARCH_K,
)
from src.rag.search import search_house_manual as _search_manual
from src.rag.search import search_local_guide as _search_guide

logger = logging.getLogger("lahore_heights.tools")


def _dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _log_tool(name: str, args: dict[str, Any], started: float, result: str) -> None:
    logger.info(
        "tool=%s args=%s duration_ms=%.1f result_bytes=%d",
        name,
        _dumps(args),
        (perf_counter() - started) * 1000.0,
        len(result.encode("utf-8")),
    )


def _error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text.strip() or f"HTTP {response.status_code}"
    if isinstance(payload, dict):
        return str(payload.get("message") or payload.get("detail") or payload)
    return str(payload)


class MockApiClient:
    """Small async client with a cached bearer token."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (MOCK_API_URL if base_url is None else base_url).strip()
        self._client: httpx.AsyncClient | None = None
        self._token: str | None = None
        self._token_lock = asyncio.Lock()

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            if self.base_url:
                self._client = httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=REQUEST_TIMEOUT_S,
                )
            else:
                # Import lazily so tests and the CLI do not create the app
                # until a tool actually needs it.
                from mock_api.app import create_app

                transport = httpx.ASGITransport(app=create_app())
                self._client = httpx.AsyncClient(
                    transport=transport,
                    base_url="http://mock-api.local",
                    timeout=REQUEST_TIMEOUT_S,
                )
        return self._client

    async def _fetch_token(self) -> str:
        if self._token:
            return self._token
        async with self._token_lock:
            if self._token:
                return self._token
            client = await self._ensure_client()
            response = await client.post(
                "/v1/accessTokens",
                json={
                    "grant_type": "client_credentials",
                    "client_id": MOCK_CLIENT_ID,
                    "client_secret": MOCK_CLIENT_SECRET,
                },
            )
            response.raise_for_status()
            self._token = str(response.json()["result"]["access_token"])
            return self._token

    async def get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        client = await self._ensure_client()
        token = await self._fetch_token()
        response = await client.get(
            path,
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        if response.status_code == 401:
            # A restarted mock API may have rotated its token. Refresh once.
            self._token = None
            token = await self._fetch_token()
            response = await client.get(
                path,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
        return response

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None


_client: MockApiClient | None = None


def get_api_client() -> MockApiClient:
    global _client
    if _client is None:
        _client = MockApiClient()
    return _client


def reset_api_client() -> None:
    """Drop the cached client (tests use this between databases)."""

    global _client
    _client = None


class CheckAvailabilityInput(BaseModel):
    check_in: str = Field(description="Check-in date in YYYY-MM-DD format.")
    check_out: str = Field(description="Check-out date in YYYY-MM-DD format (departure day).")
    guests: int | None = Field(default=None, description="Number of guests, or null if unknown.")


class ReservationInput(BaseModel):
    reservation_id: int = Field(description="The numeric reservation id.")


class SearchInput(BaseModel):
    query: str = Field(description="A short English search phrase.")


@tool("check_availability", args_schema=CheckAvailabilityInput)
async def check_availability(check_in: str, check_out: str, guests: int | None = None) -> str:
    """Check apartment availability and prices for a date range.

    Returns every listing with its nightly price and stay total. Use the year
    from the current date in the system prompt.
    """

    started = perf_counter()
    args = {"check_in": check_in, "check_out": check_out, "guests": guests}
    try:
        params: dict[str, Any] = {"checkIn": check_in, "checkOut": check_out}
        if guests is not None:
            params["guests"] = guests
        response = await get_api_client().get("/v1/availability", params=params)
        if response.status_code >= 400:
            result = _dumps({"error": _error_message(response)})
            return result
        quotes = response.json().get("result") or []
        results = [
            {
                "listing": quote.get("name"),
                "listing_id": quote.get("listingId"),
                "available": bool(quote.get("available")),
                "nightly_price_pkr": quote.get("nightlyPrice"),
                "stay_total_pkr": quote.get("stayTotal"),
                "capacity": quote.get("personCapacity"),
                "base_guests": quote.get("guestsIncluded"),
            }
            for quote in quotes
        ]
        nights = quotes[0].get("nights") if quotes else None
        result = _dumps(
            {
                "check_in": check_in,
                "check_out": check_out,
                "nights": nights,
                "guests": guests,
                "results": results,
                "note": "stay_total_pkr includes the extra guest fee when guests exceed base_guests",
            }
        )
        return result
    except Exception as exc:  # noqa: BLE001 - the model must receive a value
        result = _dumps({"error": f"{type(exc).__name__}: {exc}"})
        return result
    finally:
        _log_tool("check_availability", args, started, locals().get("result", "{}"))


@tool("get_reservation", args_schema=ReservationInput)
async def get_reservation(reservation_id: int) -> str:
    """Look up one reservation by its numeric id.

    Use the reservation id from the thread header for the guest's own booking.
    """

    started = perf_counter()
    args = {"reservation_id": reservation_id}
    try:
        response = await get_api_client().get(f"/v1/reservations/{reservation_id}")
        if response.status_code == 404:
            result = _dumps({"error": f"Reservation {reservation_id} not found"})
            return result
        if response.status_code >= 400:
            result = _dumps({"error": _error_message(response)})
            return result
        data = response.json().get("result") or {}
        deposit = data.get("securityDeposit") or {}
        result = _dumps(
            {
                "id": data.get("id"),
                "status": data.get("status"),
                "guest_name": data.get("guestName"),
                "listing": data.get("listingName"),
                "channel": data.get("channelName"),
                "arrival": data.get("arrivalDate"),
                "departure": data.get("departureDate"),
                "nights": data.get("nights"),
                "check_in_time": "2:00 PM",
                "check_out_time": "11:00 AM",
                "adults": data.get("adults"),
                "children": data.get("children"),
                "total_price_pkr": data.get("totalPrice"),
                "paid_amount_pkr": data.get("paidAmount"),
                "balance_due_pkr": data.get("balanceDue"),
                "balance_due_date": data.get("balanceDueDate"),
                "payment_status": data.get("paymentStatus"),
                "fees": data.get("fees") or [],
                "security_deposit_status": deposit.get("status"),
                "id_verification": data.get("idVerificationStatus"),
                "guest_note": data.get("guestNote") or "",
                "cancellation_date": data.get("cancellationDate"),
                "refunded_amount_pkr": data.get("refundedAmount"),
            }
        )
        return result
    except Exception as exc:  # noqa: BLE001
        result = _dumps({"error": f"{type(exc).__name__}: {exc}"})
        return result
    finally:
        _log_tool("get_reservation", args, started, locals().get("result", "{}"))


def _search_payload(results: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    key = "section" if source == "manual" else "heading_path"
    return [
        {
            "source_id": str(item.get(key, "")),
            "title": item.get("title", ""),
            "text": item.get("text", ""),
        }
        for item in results
    ]


@tool("search_house_manual", args_schema=SearchInput)
async def search_house_manual(query: str) -> str:
    """Search the building's house manual for policies, amenities and fees.

    Write the query as a short English phrase, for example "late checkout fee".
    """

    started = perf_counter()
    args = {"query": query}
    try:
        results = await asyncio.to_thread(_search_manual, query, TOOL_SEARCH_K, RAG_MODE)
        result = _dumps(_search_payload(results, "manual"))
        return result
    except Exception as exc:  # noqa: BLE001
        result = _dumps({"error": f"{type(exc).__name__}: {exc}"})
        return result
    finally:
        _log_tool("search_house_manual", args, started, locals().get("result", "{}"))


@tool("search_local_guide", args_schema=SearchInput)
async def search_local_guide(query: str) -> str:
    """Search the Lahore travel guide for sights, food, transport and the local area.

    Write the query as a short English phrase, for example "Badshahi Mosque hours".
    """

    started = perf_counter()
    args = {"query": query}
    try:
        results = await asyncio.to_thread(_search_guide, query, TOOL_SEARCH_K, RAG_MODE)
        result = _dumps(_search_payload(results, "guide"))
        return result
    except Exception as exc:  # noqa: BLE001
        result = _dumps({"error": f"{type(exc).__name__}: {exc}"})
        return result
    finally:
        _log_tool("search_local_guide", args, started, locals().get("result", "{}"))


TOOLS = [check_availability, get_reservation, search_house_manual, search_local_guide]
TOOLS_BY_NAME = {item.name: item for item in TOOLS}


def sources_from_tool_result(name: str, result: str) -> list[dict[str, Any]]:
    """Build deterministic source references from one tool result."""

    try:
        payload = json.loads(result)
    except (TypeError, ValueError):
        return []

    if name in ("search_house_manual", "search_local_guide") and isinstance(payload, list):
        source_type = "manual" if name == "search_house_manual" else "guide"
        return [
            {"type": source_type, "id": str(item["source_id"])}
            for item in payload
            if isinstance(item, dict) and item.get("source_id")
        ]

    if name == "get_reservation" and isinstance(payload, dict) and payload.get("id") is not None:
        return [{"type": "reservation", "id": str(payload["id"])}]

    if name == "check_availability" and isinstance(payload, dict) and payload.get("check_in"):
        return [{"type": "availability", "id": f"{payload['check_in']}..{payload['check_out']}"}]

    return []


def dedupe_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    unique: list[dict[str, Any]] = []
    for source in sources:
        key = (str(source.get("type", "")), str(source.get("id", "")))
        if key in seen:
            continue
        seen.add(key)
        unique.append({"type": key[0], "id": key[1]})
    return unique
