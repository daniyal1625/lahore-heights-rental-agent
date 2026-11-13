import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip real-model tests unless RUN_LLM=1."""

    if os.environ.get("RUN_LLM") == "1":
        return
    skip = pytest.mark.skip(reason="LLM test disabled; set RUN_LLM=1 to call local Ollama")
    for item in items:
        if "llm" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def seeded_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("mockdb") / "test.sqlite"
    os.environ["DATABASE_PATH"] = str(path)
    os.environ["PROJECT_ROOT"] = str(ROOT)
    os.environ["SIMULATED_NOW"] = "2026-11-10T10:00:00+05:00"
    from mock_api.seed import seed_database

    seed_database(path)
    return path


@pytest.fixture(scope="session")
def client(seeded_db: Path):
    from fastapi.testclient import TestClient
    from mock_api.app import create_app

    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def auth_header(client) -> dict[str, str]:
    response = client.post(
        "/v1/accessTokens",
        json={
            "grant_type": "client_credentials",
            "client_id": "lahore-heights",
            "client_secret": "local-dev",
        },
    )
    assert response.status_code == 200, response.text
    token = response.json()["result"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
