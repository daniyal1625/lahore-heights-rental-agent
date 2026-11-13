"""Chunk the house manual and the Wikivoyage Lahore snapshot.

The two sources have very different shapes:

* the manual is Markdown with ``## 3. Title`` and ``### 3.6 Title`` headings,
  bullet lists, tables and ``---`` rules;
* the guide is a MediaWiki plain-text extract whose headings are
  ``== Heading ==`` and ``=== Sub-heading ===``.

Both chunkers return a list of dictionaries. Every dictionary has a ``text``
key (the full chunk, breadcrumb included) plus the metadata stored in Chroma.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from src.common.text import word_count

# ---------------------------------------------------------------------------
# Manual
# ---------------------------------------------------------------------------

_H2_RE = re.compile(r"^##(?!#)\s+(\d+)\.\s+(.*?)\s*$")
_H3_RE = re.compile(r"^###(?!#)\s+(\d+)\.(\d+)\s+(.*?)\s*$")
_MANUAL_DROP_RE = re.compile(r"^\s*(?:---|\*End of manual\.\*)\s*$")

_MANUAL_MAX_BODY_WORDS = 300
_MANUAL_MAX_CHUNK_WORDS = 350


def _clean_lines(lines: Iterable[str]) -> list[str]:
    """Keep block boundaries but drop rules and document furniture."""

    cleaned: list[str] = []
    for line in lines:
        if _MANUAL_DROP_RE.match(line):
            cleaned.append("")
        elif not line.strip():
            cleaned.append("")
        else:
            cleaned.append(line.rstrip())
    return cleaned


def _blocks_from_lines(lines: Iterable[str]) -> list[str]:
    """Split on blank lines, keeping paragraphs, lists and tables intact."""

    blocks: list[str] = []
    current: list[str] = []
    for line in lines:
        if not line.strip():
            if current:
                blocks.append("\n".join(current).strip())
                current = []
        else:
            current.append(line)
    if current:
        blocks.append("\n".join(current).strip())
    return [block for block in blocks if block.strip()]


def _split_manual_blocks(blocks: list[str], max_body_words: int) -> list[list[str]]:
    """Greedily pack whole blocks into parts.

    A table or list is one block, so a row is never cut in half. If one block
    alone is larger than the limit it stays whole rather than being split
    mid-row.
    """

    if sum(word_count(block) for block in blocks) <= max_body_words:
        return [blocks]

    parts: list[list[str]] = []
    current: list[str] = []
    current_words = 0
    for block in blocks:
        block_words = word_count(block)
        if current and current_words + block_words > max_body_words:
            parts.append(current)
            current = []
            current_words = 0
        current.append(block)
        current_words += block_words
    if current:
        parts.append(current)
    return parts


def _manual_chunk(
    *,
    section: str,
    title: str,
    parent_section: str,
    breadcrumb: str,
    body_lines: Iterable[str],
) -> list[dict]:
    blocks = _blocks_from_lines(_clean_lines(body_lines))
    if not blocks:
        return []

    parts = _split_manual_blocks(blocks, _MANUAL_MAX_BODY_WORDS)

    # If a part would still push the complete chunk over the hard cap, repack
    # with a smaller body budget. The data does not need this today, but it
    # keeps the invariant true if the manual grows.
    if any(
        word_count(breadcrumb) + sum(word_count(block) for block in part)
        > _MANUAL_MAX_CHUNK_WORDS
        for part in parts
    ):
        parts = _split_manual_blocks(blocks, _MANUAL_MAX_BODY_WORDS - 60)

    chunks: list[dict] = []
    for part_index, part in enumerate(parts):
        text = breadcrumb + "\n\n" + "\n\n".join(part)
        chunks.append(
            {
                "source": "manual",
                "section": section,
                "title": title,
                "parent_section": parent_section,
                "word_count": word_count(text),
                "part": part_index,
                "part_count": len(parts),
                "text": text,
            }
        )
    return chunks


def _about_chunk(lines: list[str]) -> list[dict]:
    about_lines = [
        line.strip()
        for line in lines
        if line.strip().startswith(">") and "about this document" in line.lower()
    ]
    if not about_lines:
        return []
    body = "\n".join(about_lines)
    breadcrumb = "House manual > About this document"
    text = breadcrumb + "\n\n" + body
    return [
        {
            "source": "manual",
            "section": "0",
            "title": "About this document",
            "parent_section": "",
            "word_count": word_count(text),
            "part": 0,
            "part_count": 1,
            "text": text,
        }
    ]


def chunk_manual(path: str | Path) -> list[dict]:
    """Return one chunk per ``###`` subsection (or childless ``##``).

    The document title block is dropped. The blockquoted "About this
    document" note is kept as section ``"0"``. A subsection longer than 300
    body words is split on blank-line block boundaries; every part keeps the
    same section id and breadcrumb, and gets a ``part`` index.
    """

    lines = Path(path).read_text(encoding="utf-8").splitlines()
    first_h2 = next((i for i, line in enumerate(lines) if _H2_RE.match(line)), len(lines))

    chunks: list[dict] = []
    chunks.extend(_about_chunk(lines[:first_h2]))

    top_sections: list[dict] = []
    current_top: dict | None = None
    for line in lines[first_h2:]:
        match_h2 = _H2_RE.match(line)
        if match_h2:
            current_top = {
                "number": match_h2.group(1),
                "title": match_h2.group(2).strip(),
                "body": [],
                "children": [],
            }
            top_sections.append(current_top)
            continue

        match_h3 = _H3_RE.match(line)
        if match_h3 and current_top is not None:
            current_top["children"].append(
                {
                    "number": f"{match_h3.group(1)}.{match_h3.group(2)}",
                    "title": match_h3.group(3).strip(),
                    "body": [],
                }
            )
            continue

        if current_top is None:
            continue
        if current_top["children"]:
            current_top["children"][-1]["body"].append(line)
        else:
            current_top["body"].append(line)

    for top in top_sections:
        parent_number = top["number"]
        parent_title = top["title"]
        if top["children"]:
            for child in top["children"]:
                breadcrumb = (
                    f"House manual > {parent_number}. {parent_title} > "
                    f"{child['number']} {child['title']}"
                )
                chunks.extend(
                    _manual_chunk(
                        section=child["number"],
                        title=child["title"],
                        parent_section=parent_number,
                        breadcrumb=breadcrumb,
                        body_lines=child["body"],
                    )
                )
        else:
            breadcrumb = f"House manual > {parent_number}. {parent_title}"
            chunks.extend(
                _manual_chunk(
                    section=parent_number,
                    title=parent_title,
                    parent_section="",
                    breadcrumb=breadcrumb,
                    body_lines=top["body"],
                )
            )

    return chunks


# ---------------------------------------------------------------------------
# Guide
# ---------------------------------------------------------------------------

_GUIDE_HEADING_RE = re.compile(r"^(={2,6})\s*(.*?)\s*\1\s*$")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

_GUIDE_MAX_BODY_WORDS = 235
_GUIDE_MIN_BODY_WORDS = 120
# Reserve room for the one-sentence overlap when a section needs more than one
# chunk, so a chunk body (overlap included) still fits under the maximum.
_GUIDE_OVERLAP_ALLOWANCE = 12


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_RE.split(text) if part.strip()]


def _split_long_paragraph(paragraph: str, max_words: int) -> list[str]:
    """Split a paragraph that is longer than the chunk budget into sentences."""

    if word_count(paragraph) <= max_words:
        return [paragraph]

    units: list[str] = []
    current: list[str] = []
    current_words = 0
    for sentence in _sentences(paragraph):
        sentence_words = word_count(sentence)
        if current and current_words + sentence_words > max_words:
            units.append(" ".join(current))
            current = []
            current_words = 0
        current.append(sentence)
        current_words += sentence_words
    if current:
        units.append(" ".join(current))
    return units or [paragraph]


def _guide_paragraphs(lines: Iterable[str]) -> list[str]:
    paragraphs: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        paragraphs.extend(_split_long_paragraph(stripped, _GUIDE_MAX_BODY_WORDS))
    return paragraphs


def _pack_guide_groups(paragraphs: list[str], max_words: int) -> list[list[str]]:
    """Greedily pack paragraphs, reserving room for the next overlap sentence."""

    groups: list[list[str]] = []
    current: list[str] = []
    current_words = 0
    overlap_words = 0
    for paragraph in paragraphs:
        paragraph_words = word_count(paragraph)
        if current and overlap_words + current_words + paragraph_words > max_words:
            groups.append(current)
            overlap = _sentences(" ".join(current))
            overlap_words = word_count(overlap[-1]) if overlap else 0
            current = []
            current_words = 0
        if not current and overlap_words + paragraph_words > max_words:
            # A single paragraph plus the overlap would not fit; keep the
            # paragraph and skip the overlap at this boundary instead.
            overlap_words = 0
        current.append(paragraph)
        current_words += paragraph_words
    if current:
        groups.append(current)
    return groups


def _rebalance_guide_groups(groups: list[list[str]], min_words: int) -> None:
    """Move trailing paragraphs backwards so no tail chunk is tiny.

    Works from the last group towards the first. A group that is still short
    after borrowing from its predecessor is handled when the loop reaches that
    predecessor, so small tails cascade into an even redistribution.
    """

    for index in range(len(groups) - 1, 0, -1):
        current = groups[index]
        current_words = sum(word_count(paragraph) for paragraph in current)
        previous = groups[index - 1]
        while current_words < min_words and len(previous) > 1:
            paragraph = previous.pop()
            current.insert(0, paragraph)
            current_words += word_count(paragraph)


def _guide_chunks_for_section(
    heading_path: str,
    lines: Iterable[str],
    *,
    max_words: int = _GUIDE_MAX_BODY_WORDS,
    min_words: int = _GUIDE_MIN_BODY_WORDS,
) -> list[dict]:
    paragraphs = _guide_paragraphs(lines)
    if not paragraphs:
        return []

    total_words = sum(word_count(paragraph) for paragraph in paragraphs)
    if total_words <= max_words:
        body_parts = [paragraphs]
    else:
        groups = _pack_guide_groups(paragraphs, max_words - _GUIDE_OVERLAP_ALLOWANCE)
        _rebalance_guide_groups(groups, min_words)

        body_parts = []
        for index, group in enumerate(groups):
            body = list(group)
            if index > 0:
                previous = _sentences(" ".join(groups[index - 1]))
                overlap = previous[-1] if previous else ""
                own_words = sum(word_count(paragraph) for paragraph in group)
                if overlap and own_words + word_count(overlap) <= max_words:
                    body = [overlap, *group]
            body_parts.append(body)

    chunks: list[dict] = []
    for chunk_index, body in enumerate(body_parts):
        text = heading_path + "\n\n" + "\n\n".join(body)
        chunks.append(
            {
                "source": "guide",
                "heading_path": heading_path,
                "title": heading_path.split(" > ")[-1],
                "word_count": word_count(text),
                "chunk_index": chunk_index,
                "text": text,
            }
        )
    return chunks


def chunk_guide(path: str | Path) -> list[dict]:
    """Parse MediaWiki-style headings into ``Lahore > See > Walled City`` paths.

    Empty parent sections are skipped. Sections are packed into roughly
    120-250 body-word chunks on paragraph/line boundaries, with the last
    sentence of a chunk repeated at the start of the next chunk. Tail chunks
    are rebalanced so they do not end up much shorter than the minimum.
    """

    lines = Path(path).read_text(encoding="utf-8").splitlines()

    sections: list[tuple[str, list[str]]] = []
    current_path = "Lahore"
    buffer: list[str] = []
    stack: list[str] = []

    def flush() -> None:
        if any(line.strip() for line in buffer):
            sections.append((current_path, list(buffer)))
        buffer.clear()

    for line in lines:
        match = _GUIDE_HEADING_RE.match(line)
        if match:
            flush()
            level = len(match.group(1))
            title = match.group(2).strip()
            stack = stack[: level - 2] + [title]
            current_path = " > ".join(("Lahore", *stack))
        else:
            buffer.append(line)
    flush()

    chunks: list[dict] = []
    for heading_path, section_lines in sections:
        chunks.extend(_guide_chunks_for_section(heading_path, section_lines))
    return chunks
