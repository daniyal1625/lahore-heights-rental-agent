"""Stay overlap, protected-window, and price rules shared by the seeder and the API."""

from __future__ import annotations

from datetime import date

# Nights in this range must stay empty of Faker reservations.
# The fixed fixtures occupy it, and the eval scenarios depend on that.
PROTECTED_START = date(2026, 11, 8)
PROTECTED_END_EXCLUSIVE = date(2027, 1, 1)

RANDOM_ID_MIN = 10000
RANDOM_ID_MAX = 89999
RANDOM_RESERVATION_COUNT = 150
FAKER_SEED = 20261110


def ranges_overlap(start_a: date, end_a: date, start_b: date, end_b: date) -> bool:
    """True when half-open ranges [start_a, end_a) and [start_b, end_b) overlap."""
    return start_a < end_b and start_b < end_a


def stay_touches_protected(arrival: date, departure: date) -> bool:
    return ranges_overlap(arrival, departure, PROTECTED_START, PROTECTED_END_EXCLUSIVE)


def extra_guest_amount(listing: dict, guests: int | None, nights: int) -> int:
    """Extra-guest fee for a stay. Omitted guest count adds no fee."""
    if guests is None:
        return 0
    extra_guests = max(0, guests - int(listing["guestsIncluded"]))
    return extra_guests * nights * int(listing["extraGuestFee"])


def stay_total(listing: dict, guests: int | None, nights: int) -> int:
    """nights x nightly price + extra guest fee. Cleaning fee is 0 on these listings."""
    return nights * int(listing["price"]) + extra_guest_amount(listing, guests, nights)
