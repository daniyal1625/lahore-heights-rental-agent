"""Runtime configuration for the three Stage 3 systems.

Every value can be overridden with an environment variable. The defaults are
deliberately local and free: Ollama on the loopback interface, the in-process
mock API, and hybrid retrieval.
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = PROJECT_ROOT / "results"
RUNS_DIR = Path(os.environ.get("RUNS_DIR", RESULTS_DIR / "runs"))
SCENARIOS_PATH = Path(os.environ.get("SCENARIOS_PATH", PROJECT_ROOT / "eval" / "scenarios.json"))


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return default if value is None or value == "" else value


OLLAMA_HOST = _env("OLLAMA_HOST", "http://localhost:11434")
MODEL = _env("MODEL", "qwen2.5:3b")
TEMPERATURE = float(_env("TEMPERATURE", "0"))
SEED = int(_env("SEED", "42"))
NUM_CTX = int(_env("NUM_CTX", "4096"))
NUM_PREDICT = int(_env("NUM_PREDICT", "400"))
KEEP_ALIVE = _env("KEEP_ALIVE", "30m")
SIMULATED_NOW = _env("SIMULATED_NOW", "2026-11-10T10:00:00+05:00")

# Empty means "run the mock API in-process with httpx.ASGITransport".
MOCK_API_URL = os.environ.get("MOCK_API_URL", "").strip()
MOCK_CLIENT_ID = _env("MOCK_CLIENT_ID", "lahore-heights")
MOCK_CLIENT_SECRET = _env("MOCK_CLIENT_SECRET", "local-dev")

RAG_MODE = _env("RAG_MODE", "hybrid")

# Every Ollama call is bounded, including the agent's tool loop.
REQUEST_TIMEOUT_S = float(_env("REQUEST_TIMEOUT_S", "300"))
MAX_TOOL_ROUNDS = int(_env("MAX_TOOL_ROUNDS", "4"))

# Retrieval depths used by basic_rag.
RAG_MANUAL_K = int(_env("RAG_MANUAL_K", "3"))
RAG_GUIDE_K = int(_env("RAG_GUIDE_K", "2"))
TOOL_SEARCH_K = int(_env("TOOL_SEARCH_K", "4"))
