"""Text normalisation shared by chunking, BM25 and the retrieval evaluation.

The behaviour deliberately mirrors ``norm`` in ``eval/verify_dataset.py`` so
that evidence checks in the evaluation use the same rules as the dataset
verifier.
"""

from __future__ import annotations

import re


def normalize(text: str) -> str:
    """Lowercase, remove markdown punctuation and collapse whitespace.

    Commas and the markdown characters ``* ` _ > |`` are replaced with a
    space. Curly apostrophes and non-breaking hyphens are folded to ASCII.
    """

    text = text.lower().replace("\u2019", "'").replace("\u2011", "-")
    text = re.sub(r"[*`_>|]", " ", text).replace(",", "")
    return re.sub(r"\s+", " ", text).strip()


def word_count(text: str) -> int:
    """Whitespace word count used for chunk metadata."""

    return len(text.split())
