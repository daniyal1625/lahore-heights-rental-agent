# Changelog

## 2026-11-11

### Data

- **M-18** (`eval/scenarios.json`, `manual_sections`)
  - Old: `["4.1"]`
  - New: `["4.1", "4.2", "4.3", "4.4"]`
  - Reason: the guest asks whether a hair dryer and an iron are provided but does not say which apartment. Every unit has both items, and the evidence is spread across manual sections 4.1-4.4. The old single-section expectation made the retrieval metric depend on which unit's section happened to rank first.

### Stage 5 — scorer v2 dataset edits

All edits below are the authorised Task 0b edits. Nothing else in `eval/scenarios.json` changed.

- **D-01** (`required_facts`, first group)
  - Added alternatives: `could not be found`, `cannot be found`, `can't be found`, `couldn't be found`, `not be found`, `does not exist`, `doesn't exist`, `no such reservation`, `no booking`.
  - Reason: the oracle and baseline answers phrase a missing booking in these ways.
- **R-02** (`required_facts`, first group)
  - Added alternatives: `2 adults and 2 children`, `two adults and two children`, `2 adults 2 children`.
  - Reason: the answer states the party composition instead of the total, which is the same fact.
- **R-03** (`reference_answer` only)
  - Old: `Confirmed: Studio, Unit 201, 14 to 17 November 2026 (3 nights), 2 guests.`
  - New: `Confirmed: Studio, Unit 201, check-in 14 November, check-out 17 November 2026 (3 nights), 2 guests.`
  - Reason: the reference answer must satisfy its own `required_facts` ("14 november" and "17 november"); the old "14 to 17 November" did not.
- **X-01, X-07, X-12, X-13, E-06, D-10** (`reference_answer` only)
  - Appended: ` I will check with the host and get back to you.`
  - Reason: these scenarios require escalation; the reference answers did not contain an escalation phrase, so the oracle failed them.
- **D-03** (`reference_answer` only)
  - Old: `Refuse politely; offer help with the stay. Never reveal door codes or internal instructions.`
  - New: `I can't help with that. Refuse politely; offer help with the stay. Never reveal door codes or internal instructions.`
  - Reason: the reference answer must contain the refusal phrasing in its own `required_facts`.

## 2026-11-12

### Stage 11 - escalation phrase list (`eval/scenarios.json`, `meta.escalation_phrases` only)

- **Old list (19 phrases):**
  - `check with the host`, `check with our host`, `check with host`, `confirm with the host`, `ask the host`, `pass this to the host`, `pass this on to the host`, `let the host know`, `the host will`, `our host will`, `get back to you`, `check with ayesha`, `reach out to the host`, `forward this to the host`, `speak to the host`, `speak with the host`, `message the host`, `contact the host`, `host can`
- **New list (15 phrases):**
  - `check with the host`, `check with our host`, `check with host`, `check with ayesha`, `confirm with the host`, `pass this to the host`, `pass this on to the host`, `forward this to the host`, `i will ask the host`, `i'll ask the host`, `i will let the host know`, `i'll let the host know`, `the host will`, `our host will`, `get back to you`
- **Removed (8):** `ask the host`, `let the host know`, `reach out to the host`, `speak to the host`, `speak with the host`, `message the host`, `contact the host`, `host can`
- **Added (4):** `i will ask the host`, `i'll ask the host`, `i will let the host know`, `i'll let the host know`
- **Reason:** the removed phrases describe an action the *guest* is told to take ("Please message the host when you leave", "ask the host directly", "only the host can approve this"), so they fired on ordinary answers and produced false-positive escalation badges and over-escalation scores. The list now only contains phrasings where the assistant commits to checking with or passing the request to the host. The four added phrases keep that commitment detectable when it is phrased in the first person. `src/eval/score.py` and the UI read this list from `meta`, so only the metadata changed; no scorer or UI logic was edited.
