# Lahore Heights: a guest-messaging agent for short-term rentals

An open-source, fully local AI assistant that drafts replies to guest messages for a **fictional** short-term rental ("Lahore Heights Apartments", Lahore). It looks things up before answering (a house manual, a local travel guide, a booking system and an availability calendar) and says it will **check with the host** when it cannot find the answer.

The project is also a small, honest benchmark. It compares three ways of building the assistant on 87 test scenarios:

1. **LLM alone**: no documents, no tools.
2. **Basic RAG**: retrieved passages from the manual and the guide, no tools.
3. **RAG + tool calling**: an agent that can also read bookings and check availability. Two designs were tested: `agent_v1` (the model chooses tools itself) and `agent_v2b` (a planner chooses the tools, code runs them, the model writes the answer).

Everything runs on a laptop CPU (Intel i5-8250U, 16 GB RAM, no GPU) with a 3B model through [Ollama](https://ollama.com). No paid APIs, no private data.

## Results

Model: `qwen2.5:3b` (temperature 0, seed 42). Simulated date: 10 Nov 2026. Scores are automatic text-matching checks (see Limitations). Accuracy means all required facts present, nothing forbidden, and an escalation to the host when one is required.

### Test split (55 scenarios, 54 scored)

| System | Accuracy (95% CI) | Hallucination (strict) | Over-escalation | Correct tool choice | Median / p95 latency |
|---|---|---|---|---|---|
| LLM alone | 9.3% (4.0 to 19.9) | 3.6% | 7.3% | n/a | 7.8 s / 14.9 s |
| Basic RAG | 40.7% (28.7 to 54.0) | 0.0% | 14.5% | n/a | 43.3 s / 59.5 s |
| Agent v1 | 48.1% (35.4 to 61.2) | 1.8% | 0.0% | 60.0% | 41.0 s / 79.9 s |
| Agent v2b | 51.9% (38.9 to 64.6) | 0.0% | 9.1% | 65.4% | 46.6 s / 158.3 s |

"Hallucination (strict)" counts answers that contain a forbidden claim (for example an invented service, a leaked door code, a made-up forecast). "Over-escalation" counts answers that say "I'll check with the host" when the answer was available. "Correct tool choice" means the agent called all required tools and none that were not allowed.

### All 87 scenarios (86 scored)

| System | Accuracy (95% CI) | Hallucination (strict) | Over-escalation |
|---|---|---|---|
| LLM alone | 9.3% (4.8 to 17.3) | 2.3% | 5.7% |
| Basic RAG | 39.5% (29.9 to 50.1) | 1.1% | 12.6% |
| Agent v1 | 47.7% (37.5 to 58.1) | 3.5% | 2.3% |
| Agent v2b | 53.5% (43.0 to 63.7) | 0.0% | 12.6% |

This set includes the 32 dev scenarios that were used to improve `agent_v2b`, so its numbers are optimistic. Use the test table for claims.

### Accuracy by scenario category (all 87, passes / scored)

| Category | LLM alone | Basic RAG | Agent v1 | Agent v2b |
|---|---|---|---|---|
| Manual questions (20) | 4 | 16 | 13 | 16 |
| Local guide questions (10) | 1 | 8 | 8 | 7 |
| Availability and prices (10) | 0 | 0 | 8 | 5 |
| Own-booking questions (10) | 0 | 1 | 8 | 6 |
| Multi-tool questions (15) | 0 | 5 | 2 | 3 |
| Must escalate to host (12) | 1 | 1 | 1 | 5 |
| Edge and adversarial (9 scored) | 2 | 3 | 1 | 4 |

### What the numbers show

- **Retrieval and tools matter a lot.** The model alone invents facts (9% accuracy). Adding retrieval or tools raises accuracy to 40 to 54% (exact McNemar test, p < 0.0001 on the test split).
- **RAG and tools are good at different things.** RAG answers manual and guide questions well (80% each) but cannot see bookings or the calendar (0% on availability, 10% on bookings). The tool agents handle those (80% for `agent_v1`).
- **The planner design mainly helps with host escalation and unsafe requests.** `agent_v2b` handled 5 of 12 "check with the host" cases against 1 for the others, and refused more injection and out-of-scope requests.
- **The differences between the three RAG/agent systems are not statistically significant on the test split** (McNemar p = 0.48 RAG vs v1, 0.21 RAG vs v2b, 0.79 v1 vs v2b). Do not read a ranking into them.
- **Even the best system passes about half of the scenarios**, and answers take 40 to 160 seconds on this CPU.

## Quick start (Windows, tested from a clean copy)

Requirements: Windows 10/11, Python 3.11, [Ollama](https://ollama.com/download).

```powershell
ollama pull qwen2.5:3b

# from the project root
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1     # venv, CPU torch, packages, builds the search index (about 17 min on a clean machine)
powershell -ExecutionPolicy Bypass -File scripts\check.ps1     # dataset check and tests
powershell -ExecutionPolicy Bypass -File scripts\run_replay.ps1   # UI with saved results, no model needed
powershell -ExecutionPolicy Bypass -File scripts\run_ui.ps1       # UI with live model (Ollama must be running)
```

Open http://127.0.0.1:7860. Live replies take about 30 to 100 seconds on a CPU.

The UI has three tabs:

- **Chat (live):** pick a guest context and a system, ask a question, and see the answer, the sources, the tool calls with timings, and the raw result.
- **Compare (replay):** pick any of the 87 scenarios and see the four systems' saved answers side by side, with pass/fail.
- **Results:** the tables above and the caveats.

## How it works

- **House manual:** a fictional 7,500-word guest manual (`data/house_manual/`), split into 100 chunks by section.
- **Local guide:** a snapshot of the English Wikivoyage article "Lahore" (`data/local_guide/`), 56 chunks.
- **Search:** `BAAI/bge-small-en-v1.5` embeddings in Chroma, combined with BM25 keyword search (reciprocal rank fusion). The right manual section is in the top 5 for 97.6% of manual scenarios; median search time is about 70 ms.
- **Mock booking API:** a FastAPI + SQLite service that copies the style of the Hostaway API (`src/mock_api/`) with 13 fixed and 150 generated fake reservations.
- **Tools:** `check_availability`, `get_reservation`, `search_house_manual`, `search_local_guide`. `get_reservation` only returns the booking linked to the conversation.
- **Agents:** `agent_v1` uses native tool calling in a LangGraph loop. `agent_v2b` uses a structured-output planner, runs the tools in code, then writes the answer with the evidence.

## Project layout

```
data/        fictional manual, fake reservations, Wikivoyage snapshot
eval/        87 scenarios, dev/test split, dataset checker
results/     saved answers, reports, retrieval evaluation, review sheets
scripts/     Windows setup and run scripts
src/         agent, rag, mock_api, eval (scorer), ui, common
tests/       unit tests (no model needed)
```

## Re-running the evaluation

```powershell
python -m src.rag.eval_retrieval                      # retrieval quality
python -m src.agent run --help                        # runner options (systems, split, model)
python -m src.eval.score --model qwen2.5:3b --split test   # score saved runs (test prints aggregates only)
```

A full run of one model over all scenarios took 2 hours 24 minutes for three systems on this laptop. Runs are resumable.

## Limitations (please read)

- **Small benchmark, one author.** The 87 scenarios were written by one person (with an AI assistant), so they reflect one person's blind spots. The test split has 55 scenarios.
- **Scoring is automatic text matching.** It can be wrong in both directions. The scorer was validated with an oracle check (the written reference answers pass 86 of 86 scored scenarios) and a manual review sheet. Two scoring rules were corrected after reading baseline outputs (a wider accepted-phrase list, and the list of phrases that count as "escalating to the host"); the fixes were applied to all systems and the old and new reports are kept in `results/`.
- **Differences between RAG and the agents are not significant on the test split.**
- **The planner's example questions were written after seeing the baseline failure categories** (different facts and wording, same topics), so `agent_v2b`'s gain is probably slightly optimistic. The 32 dev scenarios were used for tuning.
- **3B model on a CPU.** Answers are slow, and the planner returns invalid JSON on a minority of turns (the code falls back to a manual search).
- **Single-turn only.** Each message is answered independently, with no conversation memory.
- **Fictional data.** The property, people, prices and policies are invented. Nothing here is real advice or real guest data.

## Licences and credits

- Code, house manual, scenarios and fake data: MIT (see `LICENSE`). The manual and scenarios were written with Claude (Anthropic).
- **Local guide text** is from the English Wikivoyage article "Lahore", licensed [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Source URL, revision and retrieval date are in `data/local_guide/SOURCE.md`. That file keeps its own licence and is not MIT.
- Models and libraries are used under their own licences (see `NOTICE.md`).
