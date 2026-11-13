"""Gradio Blocks app for the local Stage 8 demo."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, AsyncIterator

import gradio as gr

from src.ui import formatting as fmt
from src.ui.integrity import integrity_summary
from src.ui.live import check_ollama, ensure_mock_db, run_turn
from src.ui.replay import (
    categories,
    render_scenario,
    scenario_choices,
)
from src.ui.results import (
    TABLE_HEADERS,
    load_report,
    points_markdown,
    report_caption,
    table_rows,
)


def _resolve_mode(mode: str | None = None) -> str:
    value = (mode or os.environ.get("DEMO_MODE") or "live").strip().lower()
    return value if value in {"live", "replay"} else "live"


def _startup_markdown(mode: str) -> str:
    if mode == "replay":
        return (
            "**Replay mode.** New live questions are disabled here so nothing "
            "touches Ollama, Chroma or the mock API. Use the **Compare** tab to "
            "inspect saved runs. Set `DEMO_MODE=live` and restart to chat."
        )

    lines: list[str] = []
    try:
        db_path = ensure_mock_db()
        lines.append(
            f"Mock API database ready: `{Path(db_path).name}` "
            "(in-process, no separate server)."
        )
    except Exception as exc:  # pragma: no cover - defensive
        lines.append(
            "⚠️ The mock API database could not be prepared: "
            f"`{type(exc).__name__}: {exc}`"
        )

    ready, message = check_ollama()
    if ready:
        lines.append(f"✅ {message}")
    else:
        lines.append(f"### ⚠️ Ollama is not ready\n\n{message}")
    return "\n\n".join(lines)


def _append_history(
    history: list[dict[str, Any]] | None,
    question: str,
    answer: str,
) -> list[dict[str, Any]]:
    items = list(history or [])
    items.append({"role": "user", "content": question})
    items.append({"role": "assistant", "content": answer})
    return items[-6:]


def _updates(count: int) -> tuple[Any, ...]:
    return tuple(gr.update() for _ in range(count))


async def on_send(
    system: str,
    guest_label: str,
    message: str,
    history: list[dict[str, Any]] | None,
) -> AsyncIterator[tuple[Any, ...]]:
    """Run one stateless turn, yielding a working indicator first."""

    text = (message or "").strip()
    if not text:
        yield (gr.update(value="Please type a question first."), *_updates(8))
        return

    context = fmt.GUEST_CONTEXTS.get(
        guest_label, {"reservation_id": None, "guest_name": None}
    )
    yield (
        gr.update(
            value="⏳ Working… a CPU reply usually takes 30 to 90 seconds."
        ),
        *_updates(8),
    )

    try:
        result = await run_turn(system, text, context)
    except Exception as exc:  # pragma: no cover - network/model failures
        error_text = f"**Run failed:** `{type(exc).__name__}: {exc}`"
        new_history = _append_history(history, text, error_text)
        yield (
            gr.update(value=error_text),
            gr.update(value=error_text),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=[]),
            gr.update(value=""),
            gr.update(value={}),
            gr.update(value=new_history),
            gr.update(value=""),
        )
        return

    answer = str(result.get("answer") or "").strip() or (
        "_The model returned an empty answer._"
    )
    badge = fmt.escalation_badge(answer)
    sources = fmt.format_sources(result.get("sources"))
    steps = fmt.format_steps(result.get("tool_calls"))
    timings = fmt.format_timings(result)
    status = f"⚠️ Run error: `{result['error']}`" if result.get("error") else ""
    new_history = _append_history(history, text, answer)

    yield (
        gr.update(value=status),
        gr.update(value=answer),
        gr.update(value=badge),
        gr.update(value=sources),
        gr.update(value=steps),
        gr.update(value=timings),
        gr.update(value=result),
        gr.update(value=new_history),
        gr.update(value=""),
    )


def _build_chat_tab(mode: str) -> None:
    live_mode = mode == "live"
    gr.Markdown("# Chat (live)")
    gr.Markdown(_startup_markdown(mode))

    with gr.Row():
        guest_dd = gr.Dropdown(
            choices=fmt.GUEST_LABELS,
            value=fmt.GUEST_LABELS[0],
            label="Guest context",
            scale=4,
            interactive=live_mode,
        )
        system_dd = gr.Dropdown(
            choices=fmt.SYSTEM_CHOICES,
            value=fmt.DEFAULT_SYSTEM,
            label="System",
            scale=4,
            interactive=live_mode,
        )
        gr.Markdown(fmt.DEMO_DATE)

    gr.Markdown(f"**{fmt.BANNER}**")

    with gr.Row():
        message_box = gr.Textbox(
            label="Your question",
            placeholder="Ask the hospitality agent…",
            lines=2,
            scale=5,
            interactive=live_mode,
        )
        send = gr.Button(
            "Send",
            variant="primary",
            scale=1,
            interactive=live_mode,
        )

    gr.Examples(
        examples=[[question] for question in fmt.EXAMPLES],
        inputs=[message_box],
        label="Example questions (click one to load it)",
    )

    status_md = gr.Markdown("")
    with gr.Row():
        with gr.Column(scale=2):
            gr.Markdown("### Answer")
            answer_md = gr.Markdown("_No answer yet._")
            badge_md = gr.Markdown("")
        with gr.Column(scale=1):
            history_chat = gr.Chatbot(
                label="Recent turns (display only)",
                type="messages",
                height=280,
            )
            gr.Markdown(fmt.STATELESS_FOOTNOTE)

    with gr.Row():
        with gr.Column():
            gr.Markdown("### Sources")
            sources_md = gr.Markdown("_No sources yet._")
        with gr.Column():
            gr.Markdown("### Timings and tokens")
            timings_md = gr.Markdown("_No run yet._")

    gr.Markdown("### Steps")
    steps_df = gr.Dataframe(
        headers=["Tool", "Arguments", "ms"],
        value=[],
        datatype=["str", "str", "number"],
        interactive=False,
        wrap=True,
    )

    with gr.Accordion("Show raw JSON", open=False):
        raw_json = gr.JSON(value={}, label="RunResult")

    outputs = [
        status_md,
        answer_md,
        badge_md,
        sources_md,
        steps_df,
        timings_md,
        raw_json,
        history_chat,
        message_box,
    ]
    send.click(
        fn=on_send,
        inputs=[system_dd, guest_dd, message_box, history_chat],
        outputs=outputs,
        show_progress="full",
    )
    message_box.submit(
        fn=on_send,
        inputs=[system_dd, guest_dd, message_box, history_chat],
        outputs=outputs,
        show_progress="full",
    )


def _build_compare_tab() -> tuple[Any, Any, Any, Any, Any, Any]:
    gr.Markdown("# Compare (replay)")
    gr.Markdown(
        "Pick a saved scenario and compare the four systems. Badges come from "
        "the frozen scorer v2 functions."
    )

    choices = scenario_choices("All")
    default_id = choices[0][1] if choices else None

    with gr.Row():
        category_dd = gr.Dropdown(
            choices=categories(),
            value="All",
            label="Category filter",
            scale=2,
        )
        scenario_dd = gr.Dropdown(
            choices=choices,
            value=default_id,
            label="Scenario (id · category · guest message)",
            scale=5,
        )

    reference_md = gr.Markdown(fmt.format_reference(None))

    with gr.Row():
        col_llm = gr.Markdown("_Select a scenario to load saved runs._")
        col_rag = gr.Markdown("_Select a scenario to load saved runs._")
        col_v1 = gr.Markdown("_Select a scenario to load saved runs._")
        col_v2b = gr.Markdown("_Select a scenario to load saved runs._")

    gr.Markdown(fmt.REPLAY_NOTE)

    columns = [reference_md, col_llm, col_rag, col_v1, col_v2b]

    def on_category(category: str):
        filtered = scenario_choices(category)
        value = filtered[0][1] if filtered else None
        rendered = render_scenario(value)
        return (gr.update(choices=filtered, value=value), *rendered)

    category_dd.change(
        fn=on_category,
        inputs=[category_dd],
        outputs=[scenario_dd, *columns],
    )
    scenario_dd.change(
        fn=render_scenario,
        inputs=[scenario_dd],
        outputs=columns,
    )

    return scenario_dd, columns


def _build_results_tab() -> None:
    gr.Markdown("# Results")
    report = load_report()
    gr.Markdown(report_caption(report))

    rows = table_rows(report)
    if rows:
        gr.Dataframe(
            value=rows,
            headers=TABLE_HEADERS,
            datatype=["str"] * len(TABLE_HEADERS),
            interactive=False,
            wrap=True,
            label="Accuracy, hallucinations, over-escalation and latency",
        )
    else:
        gr.Markdown("_No report JSON found in `results/`._")

    with gr.Group():
        gr.Markdown("### Read this carefully")
        gr.Markdown(points_markdown(report))

    gr.Markdown(integrity_summary())


def build_blocks(mode: str | None = None) -> gr.Blocks:
    """Build the Blocks app. ``mode`` defaults to ``DEMO_MODE`` or ``live``."""

    resolved = _resolve_mode(mode)
    with gr.Blocks(
        title="Lahore Heights · Hospitality AI demo",
        analytics_enabled=False,
    ) as demo:
        with gr.Tabs():
            with gr.Tab("Chat (live)"):
                _build_chat_tab(resolved)
            with gr.Tab("Compare (replay)"):
                scenario_dd, columns = _build_compare_tab()
            with gr.Tab("Results"):
                _build_results_tab()

        gr.Markdown(fmt.GUIDE_ATTRIBUTION)

        demo.load(
            fn=render_scenario,
            inputs=[scenario_dd],
            outputs=columns,
        )

    return demo


def main() -> None:
    mode = _resolve_mode()
    demo = build_blocks(mode=mode)
    demo.queue(default_concurrency_limit=1)
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        inbrowser=False,
        show_error=True,
        show_api=False,
        quiet=False,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
