"""Paths and the simulated clock. The API never reads the real system clock."""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path

DEFAULT_SIMULATED_NOW = "2026-11-10T10:00:00+05:00"
DEFAULT_ACCESS_TOKEN = "lahore-heights-local-dev-token"
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", DEFAULT_ACCESS_TOKEN)

# Example client credentials accepted by the mock token endpoint.
# Any non-empty pair works; these are the documented local values.
DEMO_CLIENT_ID = "lahore-heights"
DEMO_CLIENT_SECRET = "local-dev"


def project_root() -> Path:
    env = os.environ.get("PROJECT_ROOT")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "DATA_README.md").is_file() and (candidate / "data" / "fixtures").is_dir():
            return candidate
    return here.parents[2]


def database_path() -> Path:
    env = os.environ.get("DATABASE_PATH")
    if env:
        return Path(env)
    return project_root() / "var" / "mock_api.sqlite"


def simulated_now() -> datetime:
    raw = os.environ.get("SIMULATED_NOW", DEFAULT_SIMULATED_NOW)
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise RuntimeError(f"SIMULATED_NOW must be an ISO-8601 datetime, got {raw!r}") from exc
    if parsed.tzinfo is None:
        raise RuntimeError("SIMULATED_NOW must include a timezone offset, for example +05:00")
    return parsed


def simulated_today() -> date:
    return simulated_now().date()
