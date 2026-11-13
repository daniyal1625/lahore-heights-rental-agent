"""End-to-end smoke tests for the local retrieval layer.

The index is a generated artefact in ``./.chroma``. If it is missing (or the
optional RAG dependencies are not installed), the index-dependent tests skip
with an explicit message instead of failing the Stage 1 suite.
"""

from __future__ import annotations

import pytest

try:  # pragma: no cover - exercised by the skip path on a clean checkout
    from src.rag.index import index_exists
    from src.rag.search import (
        search_house_manual,
        search_local_guide,
        search_with_timing,
    )
except Exception as exc:  # pragma: no cover - optional dependency missing
    _IMPORT_ERROR: Exception | None = exc
    index_exists = None  # type: ignore[assignment]
else:
    _IMPORT_ERROR = None

if _IMPORT_ERROR is not None:
    _SKIP_REASON = (
        "RAG dependencies are not installed; run "
        "`python -m pip install -e \".[rag]\"` first."
    )
elif not index_exists():
    _SKIP_REASON = (
        "Chroma index missing; run `python -m src.rag build` first "
        "(or `python -m src.rag.eval_retrieval`, which rebuilds it)."
    )
else:
    _SKIP_REASON = ""

requires_index = pytest.mark.skipif(bool(_SKIP_REASON), reason=_SKIP_REASON or "index required")


@requires_index
@pytest.mark.parametrize(
    ("query", "expected_section"),
    [
        ("wifi password for the studio", "5.1"),
        ("can I bring my dog", "11.5"),
        ("late checkout", "14.3"),
    ],
)
def test_manual_smoke_queries_return_expected_section(query: str, expected_section: str) -> None:
    for mode in ("dense", "hybrid"):
        results = search_house_manual(query, k=4, mode=mode)
        assert results, (mode, query)
        assert results[0]["section"] == expected_section, (mode, query, results[0]["section"])
        assert results[0]["rank"] == 1
        assert results[0]["text"]


@requires_index
def test_guide_smoke_query_returns_badshahi_context() -> None:
    query = "Badshahi Mosque opening hours"
    for mode in ("dense", "hybrid"):
        results = search_local_guide(query, k=4, mode=mode)
        assert results, mode
        assert results[0]["heading_path"] == "Lahore > See > Walled City"
        assert "badshahi" in results[0]["text"].lower()


@requires_index
def test_result_shape_includes_full_text_and_score() -> None:
    result = search_house_manual("wifi password for the studio", k=1)[0]
    assert set(result) >= {"rank", "section", "title", "text", "score", "source"}
    assert result["source"] == "manual"
    assert result["score"] == pytest.approx(result["score"])
    assert len(result["text"]) > 50


@requires_index
def test_search_with_timing_reports_query_latency() -> None:
    payload = search_with_timing("late checkout", source="manual", k=4, mode="dense")
    assert payload["results"]
    timings = payload["timings"]
    assert timings["source"] == "manual"
    assert timings["mode"] == "dense"
    assert timings["k"] == 4
    assert timings["total_ms"] > 0


def test_unknown_mode_is_rejected() -> None:
    if _IMPORT_ERROR is not None:
        pytest.skip(f"RAG dependencies are not installed: {_IMPORT_ERROR}")
    with pytest.raises(ValueError, match="Unknown mode"):
        search_house_manual("wifi", mode="semantic")
