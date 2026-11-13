"""Frozen-code integrity check for the Stage 8 demo.

This repeats the SHA-256 method used by ``run_meta.json`` (relative POSIX path,
NUL, file bytes, NUL) over ``src/**/*.py``, excluding the new ``src/ui``
package. It must reproduce the Stage 5 hash exactly.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from src.config import PROJECT_ROOT

FROZEN_SHA256 = "48e3c3aa867c18d686f12932e7b217f2d4dba8924b7611b4d47419efbf65e33f"
FROZEN_FILE_COUNT = 30


def frozen_code_hash(root: str | Path = PROJECT_ROOT) -> dict[str, Any]:
    """Hash only the frozen packages, never ``src/ui``."""

    root = Path(root)
    src_root = root / "src"
    digest = hashlib.sha256()
    files: list[Path] = []
    for path in sorted(src_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        relative_to_src = path.relative_to(src_root)
        if relative_to_src.parts and relative_to_src.parts[0] == "ui":
            continue
        files.append(path)

    for path in files:
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")

    return {"sha256": digest.hexdigest(), "files": len(files)}


def integrity_summary(root: str | Path = PROJECT_ROOT) -> str:
    """Return a one-line Markdown summary for the Results tab."""

    info = frozen_code_hash(root)
    matches = (
        info["sha256"] == FROZEN_SHA256 and info["files"] == FROZEN_FILE_COUNT
    )
    verdict = "**yes**" if matches else "**NO — frozen code changed**"
    return (
        f"Frozen code check (src/agent, src/rag, src/mock_api, src/eval, "
        f"src/common, src/config.py): `{info['sha256']}` · "
        f"{info['files']} files · matches Stage 5: {verdict}"
    )


__all__ = [
    "FROZEN_FILE_COUNT",
    "FROZEN_SHA256",
    "frozen_code_hash",
    "integrity_summary",
]
