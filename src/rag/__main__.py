"""Command line entry point for the retrieval layer.

Examples (PowerShell, from the repository root)::

    python -m src.rag build
    python -m src.rag search "wifi password for the studio" --source manual -k 4
    python -m src.rag search "Badshahi Mosque opening hours" --source guide -k 4 --mode hybrid
"""

from __future__ import annotations

import argparse
import json

from src.rag.config import DEFAULT_K, MODEL_NAME
from src.rag.index import build_index, index_stats
from src.rag.search import search_with_timing


def _print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local RAG index and search CLI.")
    parser.add_argument("--model", default=None, help=f"Embedding model (default: {MODEL_NAME})")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build", help="Rebuild both Chroma collections.")
    build_parser.add_argument("--model", default=None, help="Override the embedding model.")

    search_parser = subparsers.add_parser("search", help="Search one collection.")
    search_parser.add_argument("query", help="Guest query text.")
    search_parser.add_argument(
        "--source",
        choices=("manual", "guide"),
        default="manual",
        help="Which collection to search (default: manual).",
    )
    search_parser.add_argument("-k", type=int, default=DEFAULT_K, help=f"Top-k (default: {DEFAULT_K}).")
    search_parser.add_argument(
        "--mode",
        choices=("dense", "hybrid"),
        default="dense",
        help="Retrieval mode (default: dense).",
    )

    stats_parser = subparsers.add_parser("stats", help="Show chunk counts for the existing index.")
    stats_parser.set_defaults(command="stats")

    args = parser.parse_args(argv)

    if args.command == "build":
        model_name = args.model or MODEL_NAME
        stats = build_index(model_name=model_name)
        _print_json(stats)
        return 0

    if args.command == "stats":
        _print_json(index_stats())
        return 0

    if args.command == "search":
        payload = search_with_timing(
            args.query,
            source=args.source,
            k=args.k,
            mode=args.mode,
        )
        _print_json(payload)
        return 0

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
