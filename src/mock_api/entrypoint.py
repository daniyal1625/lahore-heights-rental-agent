"""Container entrypoint: seed the SQLite file on first start, then serve the API."""

from __future__ import annotations

import uvicorn

from mock_api.db import is_seeded
from mock_api.seed import seed_database
from mock_api.settings import database_path


def main() -> None:
    path = database_path()
    if not is_seeded(path):
        seed_database(path)
    uvicorn.run("mock_api.app:app", host="0.0.0.0", port=8001)


if __name__ == "__main__":
    main()
