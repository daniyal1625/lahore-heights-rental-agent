"""Dense and hybrid search over the house manual and the local guide.

Public entry points:

* ``search_house_manual(query, k=4, mode="dense")``
* ``search_local_guide(query, k=4, mode="dense")``
* ``search_with_timing(query, source=..., k=..., mode=...)``

``mode="hybrid"`` fuses the dense ranking with a BM25 ranking using
Reciprocal Rank Fusion (k=60). The BM25 index is built from the normalized
chunk text when the source is loaded.
"""

from __future__ import annotations

from time import perf_counter
from typing import Any

from src.common.text import normalize
from src.rag.config import (
    DEFAULT_K,
    HYBRID_BM25_WEIGHT,
    HYBRID_DENSE_WEIGHT,
    HYBRID_GUIDE_MIN_DEPTH,
    HYBRID_MANUAL_MIN_DEPTH,
    RRF_K,
)
from src.rag.index import encode_queries, get_collection, load_source


def _collection_name(source: str) -> str:
    if source == "manual":
        return "house_manual"
    if source == "guide":
        return "local_guide"
    raise ValueError(f"Unknown source: {source!r}")


def _dense_candidates(source: str, query: str, n_results: int) -> list[dict[str, Any]]:
    collection = get_collection(source)
    query_embedding = encode_queries([query])[0].tolist()
    response = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    ids = response.get("ids", [[]])[0]
    documents = response.get("documents", [[]])[0]
    metadatas = response.get("metadatas", [[]])[0]
    distances = response.get("distances", [[]])[0]

    candidates: list[dict[str, Any]] = []
    for chunk_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
        candidates.append(
            {
                "id": chunk_id,
                "text": document,
                "metadata": metadata,
                "dense_score": 1.0 - float(distance),
            }
        )
    return candidates


def _public_result(
    source: str,
    rank: int,
    record: dict[str, Any],
    score: float,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata = record["metadata"]
    result: dict[str, Any] = {
        "rank": rank,
        "title": metadata.get("title", ""),
        "text": record["text"],
        "score": round(float(score), 6),
        "source": source,
    }
    if source == "manual":
        result["section"] = metadata.get("section", "")
    else:
        result["heading_path"] = metadata.get("heading_path", "")
    if extra:
        result.update(extra)
    return result


def _dense_search(source: str, query: str, k: int) -> list[dict[str, Any]]:
    candidates = _dense_candidates(source, query, k)
    return [
        _public_result(source, rank, candidate, candidate["dense_score"])
        for rank, candidate in enumerate(candidates, start=1)
    ]


def _hybrid_search(source: str, query: str, k: int) -> list[dict[str, Any]]:
    if source == "manual":
        candidate_depth = max(k, HYBRID_MANUAL_MIN_DEPTH)
    else:
        candidate_depth = max(k * 4, HYBRID_GUIDE_MIN_DEPTH)
    dense_candidates = _dense_candidates(source, query, candidate_depth)
    records, bm25 = load_source(source)
    if bm25 is None or not records:
        return _dense_search(source, query, k)

    id_to_index = {record["id"]: index for index, record in enumerate(records)}
    by_id = {record["id"]: record for record in records}

    query_tokens = normalize(query).split()
    bm25_scores = bm25.get_scores(query_tokens) if query_tokens else [0.0] * len(records)
    bm25_order = sorted(
        range(len(records)),
        key=lambda index: float(bm25_scores[index]),
        reverse=True,
    )[:candidate_depth]

    rrf_scores: dict[str, float] = {}
    dense_scores: dict[str, float] = {}
    bm25_score_by_id: dict[str, float] = {}

    for rank, candidate in enumerate(dense_candidates, start=1):
        chunk_id = candidate["id"]
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + HYBRID_DENSE_WEIGHT / (RRF_K + rank)
        dense_scores[chunk_id] = float(candidate["dense_score"])

    for rank, index in enumerate(bm25_order, start=1):
        record = records[index]
        chunk_id = record["id"]
        rrf_scores[chunk_id] = rrf_scores.get(chunk_id, 0.0) + HYBRID_BM25_WEIGHT / (RRF_K + rank)
        bm25_score_by_id[chunk_id] = float(bm25_scores[index])

    # Dense-only candidates still get their BM25 score for transparency.
    for candidate in dense_candidates:
        chunk_id = candidate["id"]
        if chunk_id not in bm25_score_by_id:
            index = id_to_index.get(chunk_id)
            if index is not None:
                bm25_score_by_id[chunk_id] = float(bm25_scores[index])

    ordered = sorted(
        rrf_scores.items(),
        key=lambda item: (
            -item[1],
            -dense_scores.get(item[0], -1.0),
            -bm25_score_by_id.get(item[0], 0.0),
        ),
    )[:k]

    results: list[dict[str, Any]] = []
    for rank, (chunk_id, fused_score) in enumerate(ordered, start=1):
        record = by_id[chunk_id]
        results.append(
            _public_result(
                source,
                rank,
                record,
                fused_score,
                extra={
                    "dense_score": round(dense_scores.get(chunk_id, 0.0), 6),
                    "bm25_score": round(bm25_score_by_id.get(chunk_id, 0.0), 6),
                },
            )
        )
    return results


def _search(source: str, query: str, k: int, mode: str) -> list[dict[str, Any]]:
    if k <= 0:
        raise ValueError("k must be greater than zero")
    if mode == "dense":
        return _dense_search(source, query, k)
    if mode == "hybrid":
        return _hybrid_search(source, query, k)
    raise ValueError(f"Unknown mode: {mode!r}. Use 'dense' or 'hybrid'.")


def search_house_manual(query: str, k: int = DEFAULT_K, mode: str = "dense") -> list[dict[str, Any]]:
    return _search("manual", query, k, mode)


def search_local_guide(query: str, k: int = DEFAULT_K, mode: str = "dense") -> list[dict[str, Any]]:
    return _search("guide", query, k, mode)


def search_with_timing(
    query: str,
    source: str = "manual",
    k: int = DEFAULT_K,
    mode: str = "dense",
) -> dict[str, Any]:
    """Run one search and return results plus wall-clock query latency."""

    if source not in ("manual", "guide"):
        raise ValueError(f"Unknown source: {source!r}. Use 'manual' or 'guide'.")

    started = perf_counter()
    results = _search(source, query, k, mode)
    elapsed_ms = (perf_counter() - started) * 1000.0
    return {
        "results": results,
        "timings": {
            "total_ms": round(elapsed_ms, 3),
            "source": source,
            "mode": mode,
            "k": k,
        },
    }


def clear_caches() -> None:
    """Clear the cached collection records and BM25 index after a rebuild."""

    load_source.cache_clear()
