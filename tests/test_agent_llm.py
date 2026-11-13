"""Real-model smoke tests. Skipped unless RUN_LLM=1 and Ollama is running."""

from __future__ import annotations

import asyncio

import pytest

from src.agent.systems import run

pytestmark = pytest.mark.llm


@pytest.mark.parametrize("system", ["llm", "rag", "agent"])
def test_system_answers_check_in_question(system: str, seeded_db) -> None:
    result = asyncio.run(
        run(
            system,
            "What time is check-in and check-out?",
            {"reservation_id": None, "guest_name": None},
        )
    )
    assert result.answer
    assert result.n_llm_calls >= 1
    assert result.error is None
