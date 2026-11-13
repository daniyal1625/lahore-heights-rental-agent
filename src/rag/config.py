"""Configuration for the local retrieval layer.

Everything is local and CPU-only. The embedding model can be swapped with the
``RAG_MODEL_NAME`` environment variable; the model must be a
sentence-transformers model that works without a GPU.
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
MANUAL_PATH = DATA_DIR / "house_manual" / "lahore_heights_house_manual.md"
GUIDE_PATH = DATA_DIR / "local_guide" / "wikivoyage_lahore.txt"
CHROMA_DIR = PROJECT_ROOT / ".chroma"
RESULTS_DIR = PROJECT_ROOT / "results"

MANUAL_COLLECTION = "house_manual"
GUIDE_COLLECTION = "local_guide"
COLLECTIONS = (MANUAL_COLLECTION, GUIDE_COLLECTION)

# BAAI/bge-small-en-v1.5 is small enough for a CPU-only laptop. The exact BGE
# query instruction is applied to queries only, never to documents.
DEFAULT_MODEL_NAME = "BAAI/bge-small-en-v1.5"
MODEL_NAME = os.environ.get("RAG_MODEL_NAME", DEFAULT_MODEL_NAME)
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "

DEFAULT_K = 4
EVAL_K = 5
RRF_K = 60

# Hybrid retrieval uses weighted Reciprocal Rank Fusion. Dense retrieval is the
# primary signal; BM25 is a lexical supplement. The manual chunks are short, so
# fusing only the top-k lists keeps BM25 noise out. Guide chunks are roughly
# twice as long, so a deeper lexical list is useful there.
HYBRID_DENSE_WEIGHT = 1.5
HYBRID_BM25_WEIGHT = 1.0
HYBRID_MANUAL_MIN_DEPTH = 5
HYBRID_GUIDE_MIN_DEPTH = 20
