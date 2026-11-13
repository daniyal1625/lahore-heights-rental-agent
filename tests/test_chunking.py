"""Chunking invariants for the house manual and the Wikivoyage guide.

These tests read the real, read-only source files in ``data/`` plus a couple of
small synthetic manuals written to ``tmp_path``.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from src.common.text import word_count
from src.rag.chunking import chunk_guide, chunk_manual

ROOT = Path(__file__).resolve().parents[1]
MANUAL_PATH = ROOT / "data" / "house_manual" / "lahore_heights_house_manual.md"
GUIDE_PATH = ROOT / "data" / "local_guide" / "wikivoyage_lahore.txt"

H2_RE = re.compile(r"^##(?!#)\s+(\d+)\.\s+(.*?)\s*$")
H3_RE = re.compile(r"^###(?!#)\s+(\d+\.\d+)\s+(.*?)\s*$")


def _manual_chunks() -> list[dict]:
    return chunk_manual(MANUAL_PATH)


def _guide_chunks() -> list[dict]:
    return chunk_guide(GUIDE_PATH)


def _expected_manual_sections() -> tuple[set[str], set[str]]:
    """Return (subsection ids, childless top-level section ids)."""

    lines = MANUAL_PATH.read_text(encoding="utf-8").splitlines()
    subsections: set[str] = set()
    childless: set[str] = set()
    current_h2: str | None = None
    current_has_h3 = False
    for line in lines:
        h2 = H2_RE.match(line)
        if h2:
            if current_h2 is not None and not current_has_h3:
                childless.add(current_h2)
            current_h2 = h2.group(1)
            current_has_h3 = False
            continue
        h3 = H3_RE.match(line)
        if h3:
            subsections.add(h3.group(1))
            current_has_h3 = True
    if current_h2 is not None and not current_has_h3:
        childless.add(current_h2)
    return subsections, childless


# ---------------------------------------------------------------------------
# Manual
# ---------------------------------------------------------------------------


def test_manual_one_chunk_per_subsection_and_childless_section() -> None:
    chunks = _manual_chunks()
    subsections, childless = _expected_manual_sections()
    sections = {chunk["section"] for chunk in chunks}

    # The blockquoted About note is section "0".
    assert "0" in sections
    assert subsections <= sections
    assert childless <= sections
    assert sections == {"0"} | subsections | childless

    # Every manual chunk is one complete subsection today, so no part splits.
    assert len(chunks) == 1 + len(subsections) + len(childless)
    assert all(chunk["part_count"] == 1 for chunk in chunks)
    assert all(chunk["part"] == 0 for chunk in chunks)


def test_manual_breadcrumb_and_metadata() -> None:
    for chunk in _manual_chunks():
        assert chunk["source"] == "manual"
        assert chunk["text"].startswith("House manual > ")
        breadcrumb = chunk["text"].splitlines()[0]
        if chunk["section"] == "0":
            assert breadcrumb == "House manual > About this document"
        else:
            assert chunk["section"] in breadcrumb
            assert chunk["title"] in breadcrumb
        assert chunk["title"]
        assert set(chunk) >= {
            "source",
            "section",
            "title",
            "parent_section",
            "word_count",
            "part",
            "part_count",
            "text",
        }
        assert chunk["word_count"] == word_count(chunk["text"])


def test_manual_about_note_is_section_zero() -> None:
    about = next(chunk for chunk in _manual_chunks() if chunk["section"] == "0")
    assert about["text"].startswith("House manual > About this document")
    assert "fictional" in about["text"].lower()
    assert about["parent_section"] == ""


def test_manual_drops_title_block_and_horizontal_rules() -> None:
    joined = "\n".join(chunk["text"] for chunk in _manual_chunks())
    assert "# Lahore Heights Apartments: Guest House Manual" not in joined
    assert "**Version 2.3" not in joined
    assert not any(line.strip() == "---" for line in joined.splitlines())


def test_manual_never_splits_a_table_row() -> None:
    for chunk in _manual_chunks():
        for line in chunk["text"].splitlines():
            if line.lstrip().startswith("|"):
                # A table row must be complete: both outer pipes present.
                assert line.strip().endswith("|"), (chunk["section"], line)


def test_manual_long_subsection_splits_on_block_boundaries(tmp_path: Path) -> None:
    paragraph_a = " ".join(["alpha"] * 160)
    paragraph_b = " ".join(["beta"] * 160)
    manual = tmp_path / "manual.md"
    manual.write_text(
        "# Synthetic manual\n\n"
        "## 1. Test section\n\n"
        "### 1.1 Long subsection\n\n"
        f"{paragraph_a}\n\n{paragraph_b}\n\n"
        "### 1.2 Short subsection\n\n"
        "Short body.\n",
        encoding="utf-8",
    )

    chunks = chunk_manual(manual)
    long_chunks = [chunk for chunk in chunks if chunk["section"] == "1.1"]
    assert [chunk["part"] for chunk in long_chunks] == [0, 1]
    assert all(chunk["part_count"] == 2 for chunk in long_chunks)
    assert all(chunk["section"] == "1.1" for chunk in long_chunks)
    assert all(chunk["text"].startswith("House manual > 1. Test section > 1.1 Long subsection") for chunk in long_chunks)
    assert "alpha" in long_chunks[0]["text"]
    assert "beta" in long_chunks[1]["text"]
    assert all(chunk["word_count"] <= 350 for chunk in long_chunks)


def test_manual_keeps_a_table_in_one_piece(tmp_path: Path) -> None:
    table = "\n".join(
        ["| Item | Price |", "|---|---|", *[f"| item {index} | {index} |" for index in range(12)]]
    )
    manual = tmp_path / "manual.md"
    manual.write_text(
        "# Synthetic manual\n\n"
        "## 1. Test section\n\n"
        "### 1.1 Table subsection\n\n"
        f"{' '.join(['intro'] * 260)}\n\n{table}\n",
        encoding="utf-8",
    )

    chunks = chunk_manual(manual)
    table_chunks = [chunk for chunk in chunks if "| item 0 |" in chunk["text"]]
    assert len(table_chunks) == 1
    assert "| item 11 |" in table_chunks[0]["text"]
    assert table_chunks[0]["text"].rstrip().endswith("|")


# ---------------------------------------------------------------------------
# Guide
# ---------------------------------------------------------------------------


def test_guide_heading_paths_and_empty_parents() -> None:
    chunks = _guide_chunks()
    paths = {chunk["heading_path"] for chunk in chunks}

    assert paths
    assert all(path == "Lahore" or path.startswith("Lahore > ") for path in paths)
    assert "Lahore > See > Walled City" in paths
    assert "Lahore > Understand > History" in paths
    assert "Lahore > Get around > By metro" in paths

    # Parents with no body of their own are skipped.
    assert "Lahore > Get in" not in paths
    assert "Lahore > See" not in paths
    assert "Lahore > Buy" not in paths
    assert "Lahore > Cope" not in paths


def test_guide_breadcrumb_metadata_and_word_count() -> None:
    for chunk in _guide_chunks():
        assert chunk["source"] == "guide"
        assert chunk["text"].startswith(chunk["heading_path"] + "\n\n")
        assert chunk["title"] == chunk["heading_path"].split(" > ")[-1]
        assert set(chunk) >= {
            "source",
            "heading_path",
            "title",
            "word_count",
            "chunk_index",
            "text",
        }
        assert chunk["word_count"] == word_count(chunk["text"])


def test_guide_chunk_sizes_stay_in_range() -> None:
    chunks = _guide_chunks()
    assert max(chunk["word_count"] for chunk in chunks) <= 250

    by_path: dict[str, list[dict]] = defaultdict(list)
    for chunk in chunks:
        by_path[chunk["heading_path"]].append(chunk)

    multi = {path: items for path, items in by_path.items() if len(items) > 1}
    assert multi
    for path, items in multi.items():
        items = sorted(items, key=lambda item: item["chunk_index"])
        for chunk in items:
            body = chunk["text"].split("\n\n", 1)[1]
            assert 100 <= word_count(body) <= 250, (path, chunk["chunk_index"], word_count(body))


def test_guide_uses_one_sentence_overlap() -> None:
    by_path: dict[str, list[dict]] = defaultdict(list)
    for chunk in _guide_chunks():
        by_path[chunk["heading_path"]].append(chunk)

    checked = 0
    for path, items in by_path.items():
        items = sorted(items, key=lambda item: item["chunk_index"])
        for previous, current in zip(items, items[1:]):
            previous_body = previous["text"].split("\n\n", 1)[1].strip()
            current_body = current["text"].split("\n\n", 1)[1].strip()
            last_sentence = re.split(r"(?<=[.!?])\s+", previous_body)[-1]
            assert current_body.startswith(last_sentence), (path, previous["chunk_index"])
            checked += 1
    assert checked > 0
