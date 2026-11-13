"""Presentation helpers shared by the live and replay tabs.

Everything here is read-only: it formats a :class:`src.agent.systems.RunResult`
(or a saved JSON copy of one) and never calls a model, the mock API or Chroma.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Iterable

from src.common.text import normalize
from src.config import SCENARIOS_PATH

BANNER = (
    "Running on a CPU with a 3B model: replies take about 30 to 90 seconds."
)
DEMO_DATE = "Demo date: Tuesday 10 November 2026 (simulated)"
STATELESS_FOOTNOTE = (
    "_Each message is a single, stateless turn. The history above is shown for "
    "context only and is never sent back to the model._"
)
REPLAY_NOTE = (
    "Replay of saved runs, qwen2.5:3b, temperature 0, seed 42, "
    "simulated date 10 Nov 2026."
)
GUIDE_ATTRIBUTION = (
    "Local guide text from "
    "[Wikivoyage](https://en.wikivoyage.org/wiki/Lahore), "
    "[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)."
)
ESCALATION_TEXT = "Sent to host for confirmation"

# The five guest contexts required by the demo. The label is the dropdown
# value; the mapping is the exact ``thread_context`` sent to every system.
GUEST_CONTEXTS: dict[str, dict[str, Any]] = {
    "New enquiry (no booking)": {"reservation_id": None, "guest_name": None},
    "Sara Khan, booking 90001 (1-bedroom, arrives today)": {
        "reservation_id": 90001,
        "guest_name": "Sara Khan",
    },
    "Hamza Sheikh, booking 90004 (direct, balance due)": {
        "reservation_id": 90004,
        "guest_name": "Hamza Sheikh",
    },
    "Emily Carter, booking 90003 (Booking.com)": {
        "reservation_id": 90003,
        "guest_name": "Emily Carter",
    },
    "Chen Wei, booking 90009 (ID missing, arrives today)": {
        "reservation_id": 90009,
        "guest_name": "Chen Wei",
    },
}
GUEST_LABELS = list(GUEST_CONTEXTS)

SYSTEM_ORDER = ("llm", "rag", "agent_v1", "agent_v2b")
# These one-line descriptions mirror src/agent/variants.py. They are copied
# here (rather than imported) because importing src.agent executes its
# __init__, which pulls in Chroma and sentence-transformers even in replay mode.
SYSTEM_DESCRIPTIONS = {
    "llm": "One chat call with the shared prompt and no retrieval or tools.",
    "rag": "Automatic manual/guide retrieval followed by one chat call.",
    "agent_v1": (
        "Frozen Stage 3 tool agent: four tool rounds, parallel calls, "
        "forced final answer."
    ),
    "agent_v2b": (
        "Stage 5 planner-executor: one structured plan call, code-run tools, "
        "one answer call."
    ),
}
SYSTEM_CHOICES = [
    (f"{name} — {SYSTEM_DESCRIPTIONS[name]}", name) for name in SYSTEM_ORDER
]
DEFAULT_SYSTEM = "agent_v2b"

# Eight new example questions. These are deliberately not copied from
# eval/scenarios.json; they only exercise the same kinds of guest needs.
EXAMPLES = [
    "How late can I stay in the apartment on my last day?",
    "Is there somewhere to leave our bags after we check out?",
    "What is the quickest way to get to the airport from here?",
    "Do you provide a cot for a baby?",
    "Can we pay the remaining balance by bank transfer?",
    "Which nearby restaurants would you recommend for dinner?",
    "Is parking included, and where do we park?",
    "What should we do if the air conditioner stops working?",
]


@lru_cache(maxsize=1)
def scenario_meta() -> dict[str, Any]:
    """Read the scenario metadata (including escalation phrases) once."""

    payload = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    return dict(payload.get("meta") or {})


@lru_cache(maxsize=1)
def _manual_titles() -> dict[str, str]:
    """Map house-manual section ids to titles without loading Chroma.

    ``src.rag.chunking`` only parses the Markdown file; importing it does not
    create a Chroma client or a sentence-transformers model.
    """

    try:
        from src.rag.chunking import chunk_manual
        from src.rag.config import MANUAL_PATH

        return {
            str(chunk.get("section", "")): str(chunk.get("title", ""))
            for chunk in chunk_manual(MANUAL_PATH)
        }
    except Exception:  # pragma: no cover - only when data is unavailable
        return {}


def escalation_badge(answer: str, meta: dict[str, Any] | None = None) -> str:
    """Return the visible host-confirmation badge, or an empty string.

    The check mirrors the scorer's rule: normalise the answer and look for any
    phrase listed in ``meta.escalation_phrases``.
    """

    phrases = (meta or scenario_meta()).get("escalation_phrases") or []
    answer_norm = normalize(str(answer or ""))
    if any(normalize(str(phrase)) in answer_norm for phrase in phrases):
        return f"**{ESCALATION_TEXT}**"
    return ""


def _source_label(source: dict[str, Any]) -> str:
    source_type = str(source.get("type", "")).strip().lower()
    source_id = str(source.get("id", "")).strip()

    if source_type == "manual":
        title = _manual_titles().get(source_id, "")
        return f"Manual {source_id} — {title}" if title else f"Manual {source_id}"
    if source_type == "guide":
        return f"Guide {source_id}"
    if source_type == "reservation":
        return f"Reservation {source_id}"
    if source_type == "availability":
        return f"Availability {source_id}"
    if not source_type:
        return source_id or "Unknown source"
    return f"{source_type.title()} {source_id}".strip()


def format_sources(sources: Iterable[dict[str, Any]] | None) -> str:
    """Render the RunResult ``sources`` list as a Markdown bullet list."""

    seen: set[tuple[str, str]] = set()
    lines: list[str] = []
    for source in sources or []:
        if not isinstance(source, dict):
            continue
        key = (str(source.get("type", "")), str(source.get("id", "")))
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"- {_source_label(source)}")

    if not lines:
        return "_No retrieval or tool sources for this run._"
    return "\n".join(lines)


def format_steps(tool_calls: Iterable[dict[str, Any]] | None) -> list[list[Any]]:
    """Turn ``tool_calls`` into rows for a Gradio Dataframe."""

    rows: list[list[Any]] = []
    for call in tool_calls or []:
        if not isinstance(call, dict):
            continue
        args = call.get("args") or {}
        try:
            args_text = json.dumps(args, ensure_ascii=False, default=str)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            args_text = str(args)
        rows.append(
            [
                str(call.get("name", "")),
                args_text,
                round(float(call.get("ms") or 0.0), 1),
            ]
        )
    return rows


def format_timings(result: dict[str, Any] | None) -> str:
    """Render total/LLM/tool/retrieval seconds plus token counts."""

    if not result:
        return "_No run yet._"

    total = float(result.get("latency_s") or 0.0)
    llm_s = float(result.get("llm_s") or 0.0)
    tool_s = float(result.get("tool_s") or 0.0)
    retrieval_s = float(result.get("retrieval_s") or 0.0)
    prompt = int(result.get("prompt_tokens") or 0)
    completion = int(result.get("completion_tokens") or 0)
    calls = int(result.get("n_llm_calls") or 0)

    return (
        f"**Total:** {total:.2f} s  \n"
        f"**LLM:** {llm_s:.2f} s · **Tools:** {tool_s:.2f} s · "
        f"**Retrieval:** {retrieval_s:.2f} s  \n"
        f"**Tokens:** {prompt:,} prompt · {completion:,} completion · "
        f"{calls} LLM call{'s' if calls != 1 else ''}"
    )


def format_reference(scenario: dict[str, Any] | None) -> str:
    """Render the selected scenario header and reference answer."""

    if not scenario:
        return "_Select a scenario to load saved runs._"

    message = " ".join(str(scenario.get("guest_message", "")).split())
    reference = str(scenario.get("reference_answer", "") or "").strip()
    reference_md = reference if reference else "_No reference answer._"
    return (
        f"### {scenario.get('id', '')} · {scenario.get('category', '')}\n\n"
        f"**Guest message:** {message}\n\n"
        f"**Reference answer:** {reference_md}"
    )


def format_compare_column(
    variant: str,
    result: dict[str, Any] | None,
    score: dict[str, Any] | None = None,
) -> str:
    """Render one system column in the Compare tab."""

    if result is None:
        return f"### {variant}\n\n_No saved run for this system._"

    if score is None:
        badge = "⚪ NOT SCORED"
    else:
        passed = score.get("accuracy_pass")
        if passed is True:
            badge = "✅ **PASS**"
        elif passed is False:
            badge = "❌ **FAIL**"
        else:
            badge = "⚪ **MANUAL REVIEW**"

    answer = str(result.get("answer") or "").strip() or "_(empty answer)_"

    calls = result.get("tool_calls") or []
    if calls:
        call_lines = []
        for call in calls:
            if not isinstance(call, dict):
                continue
            args = json.dumps(call.get("args") or {}, ensure_ascii=False, default=str)
            call_lines.append(
                f"- `{call.get('name', '')}` {args} — "
                f"{float(call.get('ms') or 0.0):.0f} ms"
            )
        calls_md = "\n".join(call_lines) or "_No tool calls._"
    else:
        calls_md = "_No tool calls._"

    latency = float(result.get("latency_s") or 0.0)
    error = result.get("error")
    error_md = f"\n\n**Error:** `{error}`" if error else ""

    return (
        f"### {variant}\n\n"
        f"{badge}{error_md}\n\n"
        f"**Answer**\n\n{answer}\n\n"
        f"**Tool calls**\n\n{calls_md}\n\n"
        f"**Sources**\n\n{format_sources(result.get('sources'))}\n\n"
        f"**Latency:** {latency:.1f} s"
    )
