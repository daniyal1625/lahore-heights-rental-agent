"""Command line entry points for the Stage 3 systems.

Examples
--------
``python -m src.agent ask "What time is check-in?" --system rag``
``python -m src.agent run --systems llm,rag,agent --ids M-01,A-01``
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys

from pathlib import Path

from src.agent.runner import (
    build_run_meta,
    load_scenarios,
    run_batch,
    select_scenarios,
    utc_now,
    write_run_meta,
)
from src.agent.systems import SYSTEMS, format_reply, run, warm_up
from src.agent.variants import resolve_variant, variant_names
from src.config import MODEL, RUNS_DIR, SCENARIOS_PATH


def _parse_ids(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [item.strip() for item in raw.split(",") if item.strip()]


def _parse_systems(raw: str) -> list[str]:
    requested = [item.strip() for item in raw.split(",") if item.strip()]
    if not requested:
        raise SystemExit("At least one system is required.")
    systems: list[str] = []
    for item in requested:
        try:
            name = resolve_variant(item).name
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        if name not in systems:
            systems.append(name)
    return systems


def _thread_context(reservation_id: int | None, guest_name: str | None) -> dict:
    return {"reservation_id": reservation_id, "guest_name": guest_name}


async def _ask(args: argparse.Namespace) -> int:
    result = await run(
        args.system,
        args.message,
        _thread_context(args.reservation, args.name),
        model=args.model,
    )

    print(f"System: {result.system} | Model: {result.model}")
    if result.tool_calls:
        print("Tool calls:")
        for call in result.tool_calls:
            print(
                f"  - {call['name']}({json.dumps(call['args'], ensure_ascii=False)}) "
                f"{call['ms']:.1f} ms, {call['result_size']} bytes"
            )
    else:
        print("Tool calls: none")

    if args.verbose and result.retrieved:
        print(f"Retrieved: {', '.join(result.retrieved)}")

    print("\nReply:")
    print(format_reply(result))

    print(
        "\nTimings: "
        f"total={result.latency_s:.2f}s llm={result.llm_s:.2f}s "
        f"tool={result.tool_s:.2f}s retrieval={result.retrieval_s:.2f}s "
        f"llm_calls={result.n_llm_calls} "
        f"tokens={result.prompt_tokens}/{result.completion_tokens}"
    )
    if args.verbose and result.ollama:
        print(
            "Ollama durations (s): "
            + " ".join(f"{key}={value:.3f}" for key, value in result.ollama.items())
        )
    if result.error:
        print(f"Error: {result.error}", file=sys.stderr)
        return 1
    return 0


async def _run(args: argparse.Namespace) -> int:
    systems = _parse_systems(args.systems)
    scenarios = load_scenarios(SCENARIOS_PATH)
    selected = select_scenarios(
        scenarios,
        ids=_parse_ids(args.ids),
        category=args.category,
        split=args.split,
        all_=args.all,
    )

    log_path = Path(args.log) if args.log else None
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)

    def progress(message: str) -> None:
        print(message, flush=True)
        if log_path is not None:
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(message + "\n")

    warmup = None
    if args.warmup:
        progress(f"[warmup] loading {args.model} with one throwaway call")
        warmup = await warm_up(args.model)
        if warmup.get("ok"):
            progress(
                f"[warmup] ok {warmup['latency_s']:.1f}s "
                f"cold_load={warmup.get('cold_load_s')}s "
                f"gen={warmup.get('eval_tokens_per_s')} tok/s"
            )
        else:
            progress(f"[warmup] failed: {warmup.get('error')}")

    started_at = utc_now()
    split_label = args.split or ("all" if args.all else args.category or args.ids or "custom")
    meta_args = {
        "model": args.model,
        "variants": systems,
        "split": str(split_label),
        "scenario_count": len(selected),
        "started_at": started_at,
        "warmup": warmup,
    }
    initial_meta = await build_run_meta(
        **meta_args,
        ended_at=None,
        summary=None,
    )
    write_run_meta(args.out, args.model, initial_meta)
    progress(
        f"[start] {len(selected)} scenarios x {len(systems)} variants "
        f"= {len(selected) * len(systems)} runs"
    )

    summary = await run_batch(
        selected,
        systems,
        model=args.model,
        out_dir=args.out,
        force=args.force,
        progress=progress,
    )
    ended_at = utc_now()
    final_meta = await build_run_meta(
        **meta_args,
        ended_at=ended_at,
        summary=summary,
    )
    meta_path = write_run_meta(args.out, args.model, final_meta)
    progress(
        "Done: "
        f"{summary['completed']} written, {summary['skipped']} skipped, "
        f"{summary['failed']} with errors, {summary['elapsed_s']:.1f}s total."
    )
    progress(f"[meta] {meta_path}")
    if summary["errors"]:
        for error in summary["errors"]:
            progress(
                f"[error] {error['scenario_id']} {error['variant']}: {error['error']}"
            )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.agent",
        description="Run the LLM-only, RAG and tool-agent guest-messaging systems.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask = subparsers.add_parser("ask", help="Send one guest message to one system.")
    ask.add_argument("message", help="The guest message to answer.")
    ask.add_argument(
        "--system",
        required=True,
        choices=[*SYSTEMS, *variant_names()],
        help="System family or explicit variant name.",
    )
    ask.add_argument("--reservation", type=int, default=None, help="Reservation id for the thread header.")
    ask.add_argument("--name", default=None, help="Guest name for the thread header.")
    ask.add_argument("--model", default=MODEL)
    ask.add_argument("--verbose", action="store_true", help="Show retrieved ids and tool logs.")
    ask.set_defaults(handler=_ask)

    run_parser = subparsers.add_parser("run", help="Run a batch of evaluation scenarios.")
    run_parser.add_argument(
        "--systems",
        default="llm,rag,agent",
        help="Comma-separated systems or variants: llm,rag,agent,agent_v1",
    )
    selection = run_parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--ids", help="Comma-separated scenario ids, e.g. M-01,A-01.")
    selection.add_argument("--category", help="Only scenarios in this category.")
    selection.add_argument(
        "--split",
        choices=["dev", "test", "all"],
        help="Use the deterministic eval/split.json dev/test split.",
    )
    selection.add_argument("--all", action="store_true", help="Every scenario in eval/scenarios.json.")
    run_parser.add_argument("--model", default=MODEL)
    run_parser.add_argument("--out", default=str(RUNS_DIR), help="Output directory for result JSON files.")
    run_parser.add_argument("--force", action="store_true", help="Overwrite existing result files.")
    run_parser.add_argument("--log", help="Append progress lines to this file as well as stdout.")
    run_parser.add_argument(
        "--no-warmup",
        dest="warmup",
        action="store_false",
        help="Skip the throwaway cold-start call.",
    )
    run_parser.set_defaults(handler=_run, warmup=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if getattr(args, "verbose", False) else logging.WARNING,
        format="%(levelname)s %(name)s %(message)s",
    )
    return asyncio.run(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
