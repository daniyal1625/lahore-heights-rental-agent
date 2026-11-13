"""Live-mode helpers.

Nothing in this module imports the model stack at import time. The heavy
``src.agent.systems`` import happens only inside :func:`run_turn`, so the replay
tab can be built without loading Chroma, sentence-transformers or Ollama.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable

import httpx

from src.config import MODEL, OLLAMA_HOST


def _friendly_unreachable(host: str, model: str) -> str:
    return (
        f"Ollama is not reachable at `{host}`.\n\n"
        "Start it in a terminal with:\n\n"
        "```powershell\n"
        "ollama serve\n"
        "```\n\n"
        "Then pull the model:\n\n"
        "```powershell\n"
        f"ollama pull {model}\n"
        "```\n\n"
        "Reload this page once Ollama is running. The Compare and Results tabs "
        "work without Ollama."
    )


def _friendly_missing_model(host: str, model: str) -> str:
    return (
        f"Ollama is running at `{host}`, but the model `{model}` is not installed.\n\n"
        "Pull it with:\n\n"
        "```powershell\n"
        f"ollama pull {model}\n"
        "```\n\n"
        "Then reload this page. The Compare and Results tabs work without it."
    )


def check_ollama(
    host: str | None = None,
    model: str | None = None,
    *,
    http_get: Callable[..., Any] | None = None,
    timeout: float = 3.0,
) -> tuple[bool, str]:
    """Check whether Ollama and the requested model are available.

    ``http_get`` is injectable so tests can mock the HTTP call without a real
    server. Returns ``(ready, message)`` where ``message`` is always friendly
    enough to show in the Chat tab.
    """

    host = (host or OLLAMA_HOST).rstrip("/")
    model = model or MODEL
    get = http_get or httpx.get

    try:
        response = get(f"{host}/api/tags", timeout=timeout)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return False, _friendly_unreachable(host, model)

    names = {
        str(item.get("name", ""))
        for item in (payload.get("models") or [])
        if isinstance(item, dict)
    }
    available = model in names
    if not available and ":" not in model:
        available = any(name.split(":", 1)[0] == model for name in names)
    if not available:
        return False, _friendly_missing_model(host, model)

    return True, f"Ollama is running at `{host}` and `{model}` is available."


def ensure_mock_db() -> str:
    """Seed the in-process mock API database on first use.

    Returns the database path as a string. Importing ``mock_api`` here keeps
    replay mode completely away from the mock API package.
    """

    from mock_api.db import is_seeded
    from mock_api.seed import seed_database
    from mock_api.settings import database_path

    path = database_path()
    if not is_seeded(path):
        seed_database(path)
    return str(path)


async def run_turn(
    system: str,
    guest_message: str,
    thread_context: dict[str, Any],
) -> dict[str, Any]:
    """Run one stateless live turn and return a JSON-friendly result dict."""

    ensure_mock_db()

    # Imported lazily: this pulls in LangChain, Chroma and sentence-transformers.
    from src.agent.systems import run

    result = await run(system, guest_message, dict(thread_context))
    return asdict(result)
