"""Create the SQLite database from the fixtures, then add 150 deterministic Faker stays.

Fixed reservations are inserted unchanged. Random stays use ids 10000-89999, never
overlap on a listing, and never occupy a night in 2026-11-08..2026-12-31.
"""

from __future__ import annotations

import json
import random
import re
import unicodedata
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

from mock_api.db import connect, reset_schema
from mock_api.rules import (
    FAKER_SEED,
    RANDOM_ID_MAX,
    RANDOM_ID_MIN,
    RANDOM_RESERVATION_COUNT,
    extra_guest_amount,
    ranges_overlap,
    stay_touches_protected,
    stay_total,
)
from mock_api.settings import database_path, project_root

PAKISTANI_FIRST = (
    "Amina", "Adeel", "Bushra", "Danish", "Esha", "Farhan", "Hina", "Imran",
    "Iqra", "Junaid", "Khadija", "Laiba", "Maham", "Nida", "Noman", "Qasim",
    "Rabia", "Rizwan", "Sadia", "Sana", "Talha", "Usman", "Uzma", "Waleed",
    "Yasmin", "Yusuf", "Zara", "Zeeshan", "Hira", "Kamran",
)
PAKISTANI_LAST = (
    "Khan", "Malik", "Sheikh", "Hussain", "Iqbal", "Chaudhry", "Butt",
    "Qureshi", "Mirza", "Baig", "Dar", "Akhtar", "Nawaz", "Saleem", "Raza",
    "Siddiqui", "Farooq", "Abbasi", "Javed", "Rehman",
)
INTL_LOCALES = (
    ("en_US", "US"),
    ("en_GB", "GB"),
    ("de_DE", "DE"),
    ("fr_FR", "FR"),
    ("es_ES", "ES"),
    ("it_IT", "IT"),
    ("nl_NL", "NL"),
    ("tr_TR", "TR"),
)
CHANNELS = ("airbnbOfficial", "bookingcom", "direct")
LISTING_COUNTS = {1001: 38, 1002: 38, 1003: 37, 1004: 37}


def _load_fixture(name: str) -> list[dict]:
    path = project_root() / "data" / "fixtures" / name
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["result"]


def _ascii_slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", ".", ascii_text.lower()).strip(".")


def _place_stays(rng: random.Random, earliest: date, latest_departure: date, count: int) -> list[tuple[date, date]]:
    """Place `count` non-overlapping stays. `latest_departure` is an allowed departure date."""
    placed: list[tuple[date, date]] = []
    attempts = 0
    while len(placed) < count:
        attempts += 1
        if attempts > 20000:
            raise RuntimeError(
                f"Could only place {len(placed)} of {count} stays between {earliest} and {latest_departure}"
            )
        max_nights = min(7, (latest_departure - earliest).days)
        nights = rng.randint(1, max_nights)
        latest_arrival = latest_departure - timedelta(days=nights)
        span = (latest_arrival - earliest).days
        arrival = earliest + timedelta(days=rng.randint(0, span))
        departure = arrival + timedelta(days=nights)
        if any(ranges_overlap(arrival, departure, existing_arrival, existing_departure) for existing_arrival, existing_departure in placed):
            continue
        if stay_touches_protected(arrival, departure):
            raise RuntimeError(f"generator produced a protected-window stay {arrival}..{departure}")
        placed.append((arrival, departure))
    return placed


def _payment(rng: random.Random, status: str, total: int, arrival: date) -> dict:
    if status == "ownerStay":
        return {
            "totalPrice": 0,
            "paidAmount": 0,
            "balanceDue": 0,
            "balanceDueDate": None,
            "refundedAmount": 0,
            "paymentStatus": "unpaid",
            "cancellationDate": None,
        }
    if status == "cancelled":
        return {
            "totalPrice": total,
            "paidAmount": 0,
            "balanceDue": 0,
            "balanceDueDate": None,
            "refundedAmount": total,
            "paymentStatus": "refunded",
            "cancellationDate": (arrival - timedelta(days=rng.randint(2, 20))).isoformat(),
        }
    roll = rng.random()
    due = (arrival - timedelta(days=2)).isoformat()
    if roll < 0.7:
        return {
            "totalPrice": total,
            "paidAmount": total,
            "balanceDue": 0,
            "balanceDueDate": None,
            "refundedAmount": 0,
            "paymentStatus": "paid",
            "cancellationDate": None,
        }
    if roll < 0.9:
        paid = total // 2
        return {
            "totalPrice": total,
            "paidAmount": paid,
            "balanceDue": total - paid,
            "balanceDueDate": due,
            "refundedAmount": 0,
            "paymentStatus": "partial",
            "cancellationDate": None,
        }
    return {
        "totalPrice": total,
        "paidAmount": 0,
        "balanceDue": total,
        "balanceDueDate": due,
        "refundedAmount": 0,
        "paymentStatus": "unpaid",
        "cancellationDate": None,
    }


def _security_deposit(rng: random.Random, channel: str, status: str, payment_status: str) -> dict:
    if status in ("ownerStay", "cancelled") or channel != "direct" or rng.random() >= 0.5:
        return {"required": False, "amount": 0, "status": "not_applicable"}
    return {
        "required": True,
        "amount": 25000,
        "status": "received" if payment_status == "paid" else "pending",
    }


def _build_random_reservations(listings: list[dict], rng: random.Random) -> list[dict]:
    fakers = {locale: Faker(locale) for locale, _country in INTL_LOCALES}
    for faker in fakers.values():
        faker.seed_instance(FAKER_SEED)

    by_id = {listing["id"]: listing for listing in listings}
    stays: list[tuple[dict, date, date]] = []
    for listing_id, count in LISTING_COUNTS.items():
        early_count = count // 2
        late_count = count - early_count
        # Departure on 2026-11-08 means the last occupied night is 2026-11-07.
        early = _place_stays(rng, date(2026, 1, 6), date(2026, 11, 8), early_count)
        late = _place_stays(rng, date(2027, 1, 1), date(2027, 12, 15), late_count)
        listing = by_id[listing_id]
        stays.extend((listing, arrival, departure) for arrival, departure in early + late)

    if len(stays) != RANDOM_RESERVATION_COUNT:
        raise RuntimeError(f"expected {RANDOM_RESERVATION_COUNT} random stays, built {len(stays)}")

    ids = rng.sample(range(RANDOM_ID_MIN, RANDOM_ID_MAX + 1), RANDOM_RESERVATION_COUNT)
    ids.sort()
    stays.sort(key=lambda item: (item[1].isoformat(), item[0]["id"], item[2].isoformat()))

    records: list[dict] = []
    for index, (reservation_id, (listing, arrival, departure)) in enumerate(zip(ids, stays, strict=True)):
        nights = (departure - arrival).days
        roll = rng.random()
        if roll < 0.08:
            status = "ownerStay"
        elif roll < 0.18:
            status = "cancelled"
        elif roll < 0.30:
            status = "modified"
        else:
            status = "new"

        if status == "ownerStay":
            first, last, country = "Owner", "Block", "PK"
            adults = children = guests = 0
            total = 0
            channel = "direct"
        else:
            capacity = int(listing["personCapacity"])
            guests = rng.randint(1, capacity)
            children = rng.randint(0, min(2, guests - 1)) if guests > 1 else 0
            adults = guests - children
            total = stay_total(listing, guests, nights)
            if rng.random() < 0.6:
                first = rng.choice(PAKISTANI_FIRST)
                last = rng.choice(PAKISTANI_LAST)
                country = "PK"
            else:
                locale, country = INTL_LOCALES[rng.randrange(len(INTL_LOCALES))]
                faker = fakers[locale]
                first = faker.first_name()
                last = faker.last_name()
            channel = rng.choice(CHANNELS)

        payment = _payment(rng, status, total, arrival)
        extra = 0 if status == "ownerStay" else extra_guest_amount(listing, guests, nights)
        fees = [{"name": "Extra guest fee", "amount": extra}] if extra else []
        local = _ascii_slug(f"{first}.{last}") or f"guest{reservation_id}"
        note = ""
        if status == "ownerStay":
            note = "Owner block."
        elif rng.random() < 0.25:
            note = fakers["en_US"].sentence(nb_words=6)

        records.append(
            {
                "id": reservation_id,
                "listingMapId": listing["id"],
                "listingName": listing["name"],
                "channelName": channel,
                "status": status,
                "guestName": f"{first} {last}".strip(),
                "guestFirstName": first,
                "guestLastName": last,
                "guestEmail": f"{local}.{reservation_id}@example.com",
                "guestPhone": f"+92 302 555 {1000 + index:04d}",
                "guestCountry": country,
                "adults": adults,
                "children": children,
                "numberOfGuests": guests,
                "arrivalDate": arrival.isoformat(),
                "departureDate": departure.isoformat(),
                "nights": nights,
                "checkInTime": 14,
                "checkOutTime": 11,
                "currency": "PKR",
                "totalPrice": payment["totalPrice"],
                "paidAmount": payment["paidAmount"],
                "balanceDue": payment["balanceDue"],
                "balanceDueDate": payment["balanceDueDate"],
                "refundedAmount": payment["refundedAmount"],
                "paymentStatus": payment["paymentStatus"],
                "fees": fees,
                "securityDeposit": _security_deposit(rng, channel, status, payment["paymentStatus"]),
                "idVerificationStatus": "not_applicable" if status == "ownerStay" else rng.choice(("verified", "pending", "missing")),
                "guestNote": note,
                "reservationDate": (arrival - timedelta(days=rng.randint(7, 40))).isoformat(),
                "cancellationDate": payment["cancellationDate"],
            }
        )
    return records


def _assert_random_rules(listings: list[dict], random_rows: list[dict]) -> None:
    by_id = {listing["id"]: listing for listing in listings}
    seen: dict[int, list[tuple[date, date, int]]] = {listing_id: [] for listing_id in by_id}
    if len(random_rows) != RANDOM_RESERVATION_COUNT:
        raise RuntimeError(f"random reservation count is {len(random_rows)}")
    ids = [row["id"] for row in random_rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate random reservation ids")
    for row in random_rows:
        arrival = date.fromisoformat(row["arrivalDate"])
        departure = date.fromisoformat(row["departureDate"])
        if not RANDOM_ID_MIN <= row["id"] <= RANDOM_ID_MAX:
            raise RuntimeError(f"id {row['id']} is outside {RANDOM_ID_MIN}-{RANDOM_ID_MAX}")
        if stay_touches_protected(arrival, departure):
            raise RuntimeError(f"reservation {row['id']} touches the protected window")
        if (departure - arrival).days != row["nights"]:
            raise RuntimeError(f"reservation {row['id']} nights mismatch")
        listing = by_id[row["listingMapId"]]
        if row["numberOfGuests"] > listing["personCapacity"]:
            raise RuntimeError(f"reservation {row['id']} is over capacity")
        if row["adults"] + row["children"] != row["numberOfGuests"]:
            raise RuntimeError(f"reservation {row['id']} guest count mismatch")
        if row["status"] == "ownerStay":
            if row["totalPrice"] != 0 or row["numberOfGuests"] != 0:
                raise RuntimeError(f"owner stay {row['id']} should have zero guests and zero total")
        else:
            expected = stay_total(listing, row["numberOfGuests"], row["nights"])
            if row["totalPrice"] != expected:
                raise RuntimeError(f"reservation {row['id']} total {row['totalPrice']} != {expected}")
            if row["status"] != "cancelled" and row["totalPrice"] - row["paidAmount"] != row["balanceDue"]:
                raise RuntimeError(f"reservation {row['id']} balance mismatch")
        for other_arrival, other_departure, other_id in seen[row["listingMapId"]]:
            if ranges_overlap(arrival, departure, other_arrival, other_departure):
                raise RuntimeError(f"random overlap {row['id']} vs {other_id}")
        seen[row["listingMapId"]].append((arrival, departure, row["id"]))


def seed_database(path: Path | None = None) -> Path:
    db_path = path or database_path()
    listings = _load_fixture("listings.json")
    fixed = _load_fixture("reservations_fixed.json")
    if len(fixed) != 13:
        raise RuntimeError(f"expected 13 fixed reservations, found {len(fixed)}")
    # Sample reservation ids before stay placement so both streams stay deterministic.
    rng = random.Random(FAKER_SEED)
    random_rows = _build_random_reservations(listings, rng)
    _assert_random_rules(listings, random_rows)

    conn = connect(db_path)
    try:
        reset_schema(conn)
        conn.executemany(
            "INSERT INTO listings (id, payload) VALUES (?, ?)",
            [(listing["id"], json.dumps(listing, ensure_ascii=False)) for listing in listings],
        )
        conn.executemany(
            """
            INSERT INTO reservations (
                id, listing_map_id, arrival_date, departure_date, status, is_fixture, payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["id"],
                    row["listingMapId"],
                    row["arrivalDate"],
                    row["departureDate"],
                    row["status"],
                    1,
                    json.dumps(row, ensure_ascii=False),
                )
                for row in fixed
            ],
        )
        conn.executemany(
            """
            INSERT INTO reservations (
                id, listing_map_id, arrival_date, departure_date, status, is_fixture, payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["id"],
                    row["listingMapId"],
                    row["arrivalDate"],
                    row["departureDate"],
                    row["status"],
                    0,
                    json.dumps(row, ensure_ascii=False),
                )
                for row in random_rows
            ],
        )
        conn.execute("INSERT INTO meta (key, value) VALUES ('seeded', '1')")
        conn.execute("INSERT INTO meta (key, value) VALUES ('faker_seed', ?)", (str(FAKER_SEED),))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return db_path


def main() -> None:
    path = seed_database()
    print(
        f"Seeded 4 listings, 13 fixed reservations, and {RANDOM_RESERVATION_COUNT} "
        f"random reservations (Faker seed {FAKER_SEED}) into {path}"
    )


if __name__ == "__main__":
    main()
