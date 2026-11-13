"""SQLite connection and schema. Payloads are stored as JSON so fixtures round-trip."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
DROP TABLE IF EXISTS reservations;
DROP TABLE IF EXISTS listings;
DROP TABLE IF EXISTS meta;

CREATE TABLE listings (
    id INTEGER PRIMARY KEY,
    payload TEXT NOT NULL
);

CREATE TABLE reservations (
    id INTEGER PRIMARY KEY,
    listing_map_id INTEGER NOT NULL,
    arrival_date TEXT NOT NULL,
    departure_date TEXT NOT NULL,
    status TEXT NOT NULL,
    is_fixture INTEGER NOT NULL,
    payload TEXT NOT NULL
);

CREATE INDEX idx_reservations_listing_arrival
    ON reservations (listing_map_id, arrival_date);

CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def reset_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def is_seeded(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    conn = sqlite3.connect(path)
    try:
        row = conn.execute("SELECT value FROM meta WHERE key = 'seeded'").fetchone()
    except sqlite3.OperationalError:
        return False
    else:
        return row is not None and row[0] == "1"
    finally:
        conn.close()
