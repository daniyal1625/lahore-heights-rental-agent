"""Frozen system variants.

A variant is the pair (prompt family, graph configuration). ``agent_v1`` is the
Stage 3 agent exactly as it was frozen; later stages add new entries rather
than editing the prompt text or the graph in place. ``agent`` remains a CLI
alias for the newest agent variant, but every saved result uses the explicit
variant name.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.config import MAX_TOOL_ROUNDS


@dataclass(frozen=True)
class Variant:
    """One selectable system/prompt/graph combination."""

    name: str
    system: str
    prompt_key: str
    graph: str
    max_tool_rounds: int | None
    description: str


VARIANTS: dict[str, Variant] = {
    "llm": Variant(
        name="llm",
        system="llm",
        prompt_key="llm",
        graph="none",
        max_tool_rounds=None,
        description="One chat call with the shared prompt and no retrieval or tools.",
    ),
    "rag": Variant(
        name="rag",
        system="rag",
        prompt_key="rag",
        graph="none",
        max_tool_rounds=None,
        description="Automatic manual/guide retrieval followed by one chat call.",
    ),
    "agent_v1": Variant(
        name="agent_v1",
        system="agent",
        prompt_key="agent",
        graph="tool_agent_v1",
        max_tool_rounds=MAX_TOOL_ROUNDS,
        description="Frozen Stage 3 tool agent: four tool rounds, parallel calls, forced final answer.",
    ),
    "agent_v2b": Variant(
        name="agent_v2b",
        system="agent",
        prompt_key="agent_v2b",
        graph="planner_executor_v2b",
        max_tool_rounds=None,
        description="Stage 5 planner-executor: one structured plan call, code-run tools, one answer call.",
    ),
}

# Backwards-compatible aliases. They are resolved before a result is written.
ALIASES = {"agent": "agent_v1"}

# The newest variant for each system family. ``--system agent`` resolves here.
NEWEST_BY_SYSTEM = {"llm": "llm", "rag": "rag", "agent": "agent_v1"}

SYSTEMS = tuple(NEWEST_BY_SYSTEM)
VARIANT_NAMES = tuple(VARIANTS)


def resolve_variant(name: str) -> Variant:
    """Resolve an explicit variant name or a backwards-compatible alias."""

    key = ALIASES.get(name, name)
    try:
        return VARIANTS[key]
    except KeyError as exc:
        choices = ", ".join(VARIANT_NAMES)
        raise ValueError(f"Unknown variant {name!r}. Use one of {choices} (or alias agent).") from exc


def newest_variant(system: str) -> Variant:
    """Return the newest variant for a system family."""

    try:
        return VARIANTS[NEWEST_BY_SYSTEM[system]]
    except KeyError as exc:
        raise ValueError(f"Unknown system {system!r}. Use one of {', '.join(SYSTEMS)}.") from exc


def variant_names() -> list[str]:
    return list(VARIANT_NAMES)
