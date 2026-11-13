"""Tests for the Stage 8 Gradio demo. No Ollama server is needed."""

from __future__ import annotations

import httpx

from src.ui.formatting import escalation_badge, format_sources
from src.ui.live import check_ollama
from src.ui.replay import load_run, run_path


def test_replay_loader_reads_real_runs_and_skips_missing() -> None:
    for variant in ("llm", "rag", "agent_v1", "agent_v2b"):
        result = load_run("A-01", variant)
        assert result is not None
        assert result["scenario_id"] == "A-01"
        assert result["variant"] == variant
        assert result["answer"]

    assert load_run("ZZ-99", "agent_v2b") is None
    assert load_run("A-01", "not_a_variant") is None
    assert not run_path("ZZ-99", "agent_v2b").exists()


def test_escalation_badge_helper() -> None:
    meta = {
        "escalation_phrases": [
            "check with the host",
            "the host will",
        ]
    }
    badge = escalation_badge("I'll check with the host and let you know.", meta)
    assert badge == "**Sent to host for confirmation**"

    assert escalation_badge("Check-in is at 2:00 PM.", meta) == ""
    assert escalation_badge("THE HOST WILL confirm the late checkout.", meta)


def test_sources_formatter_includes_ids_and_titles() -> None:
    text = format_sources(
        [
            {"type": "manual", "id": "3.6"},
            {"type": "guide", "id": "Lahore > See > Walled City"},
            {"type": "reservation", "id": "90001"},
            {"type": "availability", "id": "2026-11-12..2026-11-14"},
        ]
    )
    assert "Manual 3.6 — Early check-in and luggage storage" in text
    assert "Guide Lahore > See > Walled City" in text
    assert "Reservation 90001" in text
    assert "Availability 2026-11-12..2026-11-14" in text

    assert format_sources([]) == "_No retrieval or tool sources for this run._"


def test_blocks_build_in_replay_without_ollama_or_mock_api(monkeypatch) -> None:
    import gradio as gr

    import src.ui.app as app

    def fail(*args, **kwargs):
        raise AssertionError("replay mode must not contact Ollama or the mock API")

    monkeypatch.setenv("DEMO_MODE", "replay")
    monkeypatch.setattr(app, "check_ollama", fail)
    monkeypatch.setattr(app, "ensure_mock_db", fail)

    demo = app.build_blocks(mode="replay")
    assert isinstance(demo, gr.Blocks)


def test_startup_check_is_friendly_when_ollama_is_unreachable() -> None:
    def unreachable(url, timeout):
        raise httpx.ConnectError("connection refused")

    ready, message = check_ollama(http_get=unreachable)
    assert ready is False
    assert "Ollama is not reachable" in message
    assert "ollama serve" in message
    assert "ollama pull qwen2.5:3b" in message

    class MissingModelResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self):
            return {"models": [{"name": "llama3:8b"}]}

    def missing_model(url, timeout):
        return MissingModelResponse()

    ready, message = check_ollama(http_get=missing_model)
    assert ready is False
    assert "ollama pull qwen2.5:3b" in message
