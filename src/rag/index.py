"""Build and load the local Chroma index.

The index lives in ``./.chroma`` and has one collection per source. Embeddings
are produced explicitly with sentence-transformers, so Chroma's default
embedding function is never used.
"""

from __future__ import annotations

import statistics
from functools import lru_cache
from pathlib import Path
from time import perf_counter
from typing import Any

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from src.common.text import normalize
from src.rag.chunking import chunk_guide, chunk_manual
from src.rag.config import (
    CHROMA_DIR,
    COLLECTIONS,
    GUIDE_COLLECTION,
    GUIDE_PATH,
    MANUAL_COLLECTION,
    MANUAL_PATH,
    MODEL_NAME,
)


@lru_cache(maxsize=1)
def get_client() -> chromadb.PersistentClient:
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )


@lru_cache(maxsize=4)
def get_model(model_name: str = MODEL_NAME) -> SentenceTransformer:
    return SentenceTransformer(model_name, device="cpu")


def encode_documents(texts: list[str], *, model_name: str = MODEL_NAME):
    """Encode documents without the BGE query instruction."""

    return get_model(model_name).encode(
        texts,
        batch_size=32,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )


def encode_queries(texts: list[str], *, model_name: str = MODEL_NAME):
    """Encode queries with the exact BGE instruction prefix."""

    from src.rag.config import QUERY_PREFIX

    prefixed = [QUERY_PREFIX + text for text in texts]
    return get_model(model_name).encode(
        prefixed,
        batch_size=32,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )


def _collection_name(source: str) -> str:
    if source == "manual":
        return MANUAL_COLLECTION
    if source == "guide":
        return GUIDE_COLLECTION
    raise ValueError(f"Unknown source: {source!r}")


def get_collection(source: str):
    name = _collection_name(source)
    client = get_client()
    try:
        return client.get_collection(name, embedding_function=None)
    except Exception as exc:  # Chroma raises different errors across versions.
        raise FileNotFoundError(
            f"Chroma collection {name!r} is missing. "
            "Run `python -m src.rag build` first."
        ) from exc


def index_exists() -> bool:
    try:
        for source in ("manual", "guide"):
            if get_collection(source).count() == 0:
                return False
        return True
    except Exception:
        return False


def _metadata(chunk: dict) -> dict[str, Any]:
    return {key: value for key, value in chunk.items() if key != "text"}


def _chunk_stats(chunks: list[dict]) -> dict[str, Any]:
    words = [int(chunk["word_count"]) for chunk in chunks]
    return {
        "chunks": len(chunks),
        "avg_words": round(statistics.mean(words), 2) if words else 0.0,
        "max_words": max(words) if words else 0,
        "min_words": min(words) if words else 0,
    }


def _delete_collection(client, name: str) -> None:
    try:
        client.delete_collection(name)
    except Exception:
        # It is fine if the collection does not exist yet.
        pass


def build_index(
    *,
    manual_path: str | Path = MANUAL_PATH,
    guide_path: str | Path = GUIDE_PATH,
    model_name: str = MODEL_NAME,
) -> dict[str, Any]:
    """Rebuild both collections from scratch. Idempotent."""

    started = perf_counter()
    manual_chunks = chunk_manual(manual_path)
    guide_chunks = chunk_guide(guide_path)

    # Touch the model before timing the index work so a first-run download is
    # visible but does not distort the per-collection encode measurement.
    model = get_model(model_name)

    client = get_client()
    for name in COLLECTIONS:
        _delete_collection(client, name)

    per_collection: dict[str, dict[str, Any]] = {}
    for source, name, chunks in (
        ("manual", MANUAL_COLLECTION, manual_chunks),
        ("guide", GUIDE_COLLECTION, guide_chunks),
    ):
        collection = client.create_collection(
            name=name,
            metadata={"hnsw:space": "cosine", "embedding_model": model_name},
            embedding_function=None,
        )
        ids = []
        if source == "manual":
            ids = [f"manual-{chunk['section']}-p{chunk['part']}" for chunk in chunks]
        else:
            ids = [f"guide-{index:04d}" for index in range(len(chunks))]
        documents = [chunk["text"] for chunk in chunks]
        metadatas = [_metadata(chunk) for chunk in chunks]

        embeddings = model.encode(
            documents,
            batch_size=32,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        batch_size = 128
        for start in range(0, len(chunks), batch_size):
            end = start + batch_size
            collection.add(
                ids=ids[start:end],
                documents=documents[start:end],
                metadatas=metadatas[start:end],
                embeddings=embeddings[start:end].tolist(),
            )

        per_collection[source] = _chunk_stats(chunks)
        per_collection[source]["collection"] = name
        per_collection[source]["model"] = model_name

    elapsed = perf_counter() - started

    # The search module caches the collection records and BM25 index.
    try:
        from src.rag.search import clear_caches

        clear_caches()
    except Exception:
        pass

    return {
        "build_time_s": round(elapsed, 3),
        "chunks": {
            "manual": per_collection["manual"]["chunks"],
            "guide": per_collection["guide"]["chunks"],
            "total": per_collection["manual"]["chunks"] + per_collection["guide"]["chunks"],
        },
        "words": {
            "manual": {
                "avg": per_collection["manual"]["avg_words"],
                "max": per_collection["manual"]["max_words"],
                "min": per_collection["manual"]["min_words"],
            },
            "guide": {
                "avg": per_collection["guide"]["avg_words"],
                "max": per_collection["guide"]["max_words"],
                "min": per_collection["guide"]["min_words"],
            },
        },
        "collections": per_collection,
    }


@lru_cache(maxsize=2)
def load_source(source: str) -> tuple[list[dict[str, Any]], Any]:
    """Load all chunks and build the BM25 index for one source.

    The returned tuple is ``(records, bm25)``. Records are dictionaries with
    ``id``, ``text`` and ``metadata``. BM25 is built over the normalized chunk
    text, exactly the text a guest query is compared with.
    """

    from rank_bm25 import BM25Okapi

    collection = get_collection(source)
    payload = collection.get(include=["documents", "metadatas"])
    ids = payload.get("ids") or []
    documents = payload.get("documents") or []
    metadatas = payload.get("metadatas") or []

    records = [
        {"id": chunk_id, "text": document, "metadata": metadata}
        for chunk_id, document, metadata in zip(ids, documents, metadatas)
    ]
    tokenized = [normalize(record["text"]).split() for record in records]
    bm25 = BM25Okapi(tokenized) if tokenized else None
    return records, bm25


def index_stats() -> dict[str, Any]:
    """Compute chunk counts and word statistics from an existing index."""

    stats: dict[str, Any] = {"chunks": {}, "words": {}}
    total = 0
    for source in ("manual", "guide"):
        records, _ = load_source(source)
        words = [int(record["metadata"]["word_count"]) for record in records]
        stats["chunks"][source] = len(records)
        total += len(records)
        stats["words"][source] = {
            "avg": round(statistics.mean(words), 2) if words else 0.0,
            "max": max(words) if words else 0,
            "min": min(words) if words else 0,
        }
    stats["chunks"]["total"] = total
    return stats
