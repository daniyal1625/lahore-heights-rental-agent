# Lahore Heights: dataset and evaluation notes

All data is fictional or public. Nothing here comes from a company or a real guest.

## Files

| Path | What it is |
|---|---|
| `data/house_manual/lahore_heights_house_manual.md` | Fictional house manual (about 7,500 words, 21 numbered sections). Written with Claude. Ingest this for `search_house_manual`. |
| `data/fixtures/listings.json` | 4 listings (Hostaway-style fields). Seed the mock API with these exactly. |
| `data/fixtures/reservations_fixed.json` | 13 fixed reservations (IDs 90001 to 90013). The test scenarios depend on them. |
| `eval/scenarios.json` | 87 test scenarios plus `meta` (rules, escalation phrases, tool signatures). |
| `eval/verify_dataset.py` | Consistency checker. Run it after every change to the manual or fixtures. |

You still need to add `data/local_guide/` yourself: a saved snapshot of the English Wikivoyage article "Lahore" (CC BY-SA 4.0 or the licence shown on the page; keep the page URL, the revision/`oldid` and the retrieval date in a `SOURCE.md` and credit it in the README and the app UI).

## The simulated world

- **"Today" is fixed**: `2026-11-10T10:00:00+05:00` (Tuesday, Asia/Karachi). Inject it into every system prompt. Do not use the real clock in tests.
- Prices (PKR per night): Studio 9,500; One-Bedroom 14,000; Two-Bedroom 21,000; Penthouse 38,000. Extra guest fee 2,000 per guest per night above base occupancy.
- A night is occupied if `arrival <= night < departure`. A departure day and an arrival day may be the same day (same-day turnover). Only cancelled reservations are ignored; `ownerStay` blocks the calendar.
- Listing IDs: 1001 Studio, 1002 One-Bedroom, 1003 Two-Bedroom, 1004 Penthouse.

## Rules for the Faker script (important)

1. Always insert the fixed fixtures first, unchanged.
2. Random reservations must use IDs outside 90001 to 90013 (for example 10000 to 89999).
3. Random reservations must stay out of the **protected window `2026-11-08` to `2026-12-31`** on every listing, otherwise availability scenarios change. Put them in earlier months of 2026 or in 2027.
4. Keep Hostaway-style naming (`listingMapId`, `arrivalDate`, `departureDate`, `numberOfGuests`, `channelName`, `status`, `totalPrice`, `currency`) and wrap responses as `{"status": "success", "result": ...}`.

## Tool signatures used by the scenarios

```
check_availability(check_in: "YYYY-MM-DD", check_out: "YYYY-MM-DD", guests: int | None)
    -> for each listing: available (bool), nightly price, total for the stay, capacity, base occupancy
get_reservation(reservation_id: int)  -> the reservation object, or a not-found error
search_house_manual(query: str)       -> top-k manual chunks with section ids
search_local_guide(query: str)        -> top-k guide chunks
```

Chunk the manual by its `##`/`###` headings and keep the section number (for example `3.6`) as metadata. It lets you measure retrieval hit rate against `manual_sections` in each scenario.

## What each system gets

1. **LLM alone:** guest message, `thread_context`, simulated date. No retrieval, no tools.
2. **Basic RAG:** same, plus the top-k chunks from the manual and the guide (retrieved automatically).
3. **RAG + tools (agent):** same, plus the four tools and the reservation id from `thread_context`.

`thread_context` mimics the booking thread a message arrives in: it holds the reservation id (or `null` for pre-booking enquiries) and the guest name. Systems 1 and 2 can see the id but cannot look it up, so they should not be able to answer `reservation_only` and most `multi_tool` scenarios correctly. That is the point of the comparison.

## Scenario schema

| Field | Meaning |
|---|---|
| `category` | `manual_only`, `guide_only`, `availability_only`, `reservation_only`, `multi_tool`, `must_escalate`, `edge_adversarial` |
| `required_tools` / `optional_tools` | Tool choice is correct when `required ⊆ called ⊆ required ∪ optional` |
| `expected_args` | Expected tool arguments (check them for the `check_availability` and `get_reservation` calls) |
| `required_facts` | List of groups. Every group needs at least one of its alternatives in the answer (all-of across groups, any-of inside) |
| `forbidden_substrings`, `forbidden_regex` | Any hit counts as a hallucination or policy violation |
| `must_escalate_to_host` | Answer must contain one of `meta.escalation_phrases`; the gap scenarios also forbid invented prices |
| `reference_answer` | Human-readable gold answer (use for an optional LLM judge and for error analysis) |
| `judge_rubric` | Extra rule for hard cases that substring matching cannot check |
| `manual_sections`, `manual_evidence` | Where the answer lives in the manual (verified by `verify_dataset.py`) |
| `guide_evidence` | Words that must exist in your Wikivoyage snapshot (verified with `--guide`) |
| `expected_available_listing_ids` | Gold availability result, recomputed from fixtures by the verifier |
| `difficulty` | `easy` / `medium` / `hard` |

Normalise before matching: lowercase, remove commas and asterisks, treat "PKR" and "Rs" as optional. A deterministic check can be wrong in both directions, so spot-check 10 to 15 answers by hand and report that you did.

## Metrics (suggested definitions)

- **Accuracy:** all `required_facts` groups matched, no forbidden hit, and the escalation phrase present when required.
- **Correct tool choice:** see the rule above (systems 1 and 2 score "n/a").
- **Hallucination rate:** answers with a forbidden hit, a wrong number, or a made-up service, divided by all answers.
- **Response time:** wall-clock seconds per scenario on the CPU laptop, with the model name and quantisation in the results table.

## Known limits (state them in your README)

- The scenarios are written by one author, so they carry that author's blind spots.
- Substring matching is a proxy for correctness.
- The 12 guide scenarios depend on the Wikivoyage article at the time you snapshot it. Run `python eval/verify_dataset.py --guide <snapshot>`; any `WARN` line means a scenario should be reworded or dropped.
