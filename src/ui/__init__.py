"""Local Gradio demo app for the Lahore Heights hospitality agent.

The package only imports the frozen Stage 3-5 code. Launch it with::

    python -m src.ui

Set ``DEMO_MODE=replay`` to browse saved runs without touching Ollama, Chroma
or the mock API.
"""

from __future__ import annotations

__all__ = ["build_blocks", "main"]


def build_blocks(*args, **kwargs):  # pragma: no cover - thin import wrapper
    """Import the app lazily so importing ``src.ui`` stays cheap."""

    from src.ui.app import build_blocks as _build_blocks

    return _build_blocks(*args, **kwargs)


def main() -> None:  # pragma: no cover - launch wrapper
    from src.ui.app import main as _main

    _main()
