"""Rule-level tests for the automatic scorer."""

from __future__ import annotations

import math

from src.eval.score import (
    _mcnemar,
    _source_check,
    _tool_check,
    _wilson,
    evaluate_answer,
    load_scenarios,
    render_markdown,
    score_result,
)

META = {
    "escalation_phrases": [
        "check with the host",
        "check with our host",
        "check with host",
        "check with ayesha",
        "confirm with the host",
        "pass this to the host",
        "pass this on to the host",
        "forward this to the host",
        "i will ask the host",
        "i'll ask the host",
        "i will let the host know",
        "i'll let the host know",
        "the host will",
        "our host will",
        "get back to you",
    ]
}


def _scenario(**overrides):
    scenario = {
        "id": "T-01",
        "category": "manual_only",
        "difficulty": "easy",
        "guest_message": "What time is check-in?",
        "thread_context": {"reservation_id": None, "guest_name": None},
        "required_tools": [],
        "optional_tools": [],
        "expected_args": {},
        "required_facts": [["2:00 pm", "2 pm", "14:00"]],
        "forbidden_substrings": [],
        "forbidden_regex": [],
        "must_escalate_to_host": False,
        "behavior": None,
        "judge_rubric": None,
        "manual_sections": [],
        "guide_evidence": [],
    }
    scenario.update(overrides)
    return scenario


def test_facts_are_any_of_inside_and_all_of_across() -> None:
    scenario = _scenario(required_facts=[["2:00 pm", "2 pm"], ["11:00 am", "11 am"]])
    good = evaluate_answer(scenario, "Check-in 2 PM, check-out 11 AM.", META)
    assert good["facts_ok"] is True
    assert good["missed_fact_groups"] == []

    missing_one = evaluate_answer(scenario, "Check-in is 2 PM.", META)
    assert missing_one["facts_ok"] is False
    assert missing_one["missed_fact_groups"] == [["11:00 am", "11 am"]]


def test_pkr_and_rs_are_optional_in_required_facts() -> None:
    scenario = _scenario(required_facts=[["pkr 2500", "2500"]])
    assert evaluate_answer(scenario, "The fee is PKR 2,500.", META)["facts_ok"] is True
    assert evaluate_answer(scenario, "The fee is 2500.", META)["facts_ok"] is True


def test_forbidden_substring_and_regex() -> None:
    scenario = _scenario(
        required_facts=[],
        must_escalate_to_host=True,
        forbidden_substrings=["refund approved"],
        forbidden_regex=[r"(pkr|rs\.?)\s?\d"],
    )
    substring = evaluate_answer(scenario, "Your refund approved. Check with the host.", META)
    assert substring["forbidden_hit"] is True
    assert substring["accuracy_pass"] is False

    regex = evaluate_answer(scenario, "It costs PKR 5,000. Check with the host.", META)
    assert regex["forbidden_hit"] is True

    clean = evaluate_answer(scenario, "I will check with the host and get back to you.", META)
    assert clean["forbidden_hit"] is False
    assert clean["accuracy_pass"] is True


def test_e_scenario_forbidden_regex_from_dataset() -> None:
    scenarios, meta = load_scenarios()
    e01 = next(scenario for scenario in scenarios if scenario["id"] == "E-01")
    bad = evaluate_answer(e01, "It costs Rs. 2,000. I will check with the host.", meta)
    assert bad["forbidden_hit"] is True
    assert bad["accuracy_pass"] is False
    good = evaluate_answer(e01, "I will check with the host and get back to you.", meta)
    assert good["forbidden_hit"] is False
    assert good["accuracy_pass"] is True


def test_escalation_and_over_escalation() -> None:
    escalate = _scenario(must_escalate_to_host=True, required_facts=[])
    answer = "I will check with the host and get back to you."
    rules = evaluate_answer(escalate, answer, META)
    assert rules["escalated"] is True
    assert rules["escalation_ok"] is True
    assert rules["over_escalation"] is False

    normal = _scenario(must_escalate_to_host=False)
    rules = evaluate_answer(normal, "Check-in is 2 PM. I will check with the host.", META)
    assert rules["escalated"] is True
    assert rules["escalation_ok"] is True
    assert rules["over_escalation"] is True


def test_guest_instruction_is_not_escalation() -> None:
    """Telling the guest to message the host is not the assistant escalating."""

    scenarios, meta = load_scenarios()
    scenario = next(item for item in scenarios if item["id"] == "M-01")
    rules = evaluate_answer(
        scenario, "Check-out is at 11:00 AM. Please message the host when you leave.", meta
    )
    assert rules["escalated"] is False
    assert rules["over_escalation"] is False


def test_first_person_host_check_is_escalation() -> None:
    """The assistant committing to check with the host must still count."""

    scenarios, meta = load_scenarios()
    scenario = next(item for item in scenarios if item["id"] == "M-01")
    rules = evaluate_answer(
        scenario, "I will check with the host and get back to you.", meta
    )
    assert rules["escalated"] is True
    assert rules["over_escalation"] is True


def test_roman_urdu_d06_alternatives() -> None:
    scenarios, meta = load_scenarios()
    d06 = next(scenario for scenario in scenarios if scenario["id"] == "D-06")
    roman_urdu = evaluate_answer(d06, "Check-in 2 baje, check-out gyarah baje.", meta)
    assert roman_urdu["facts_ok"] is True
    assert roman_urdu["accuracy_pass"] is True

    english = evaluate_answer(d06, "Check-in is 2:00 PM and check-out is 11:00 AM.", meta)
    assert english["facts_ok"] is True


def test_manual_review_scenario_is_none() -> None:
    scenarios, meta = load_scenarios()
    d09 = next(scenario for scenario in scenarios if scenario["id"] == "D-09")
    rules = evaluate_answer(d09, "Which dates and how many guests?", meta)
    assert rules["manual_review"] is True
    assert rules["accuracy_pass"] is None


def test_empty_answer_fails_every_scenario_with_required_facts() -> None:
    scenarios, meta = load_scenarios()
    for scenario in scenarios:
        if scenario.get("required_facts"):
            rules = evaluate_answer(scenario, "", meta)
            assert rules["accuracy_pass"] is False, scenario["id"]


def test_tool_selection_and_argument_checks() -> None:
    scenario = _scenario(
        required_tools=["check_availability"],
        optional_tools=[],
        expected_args={
            "check_availability": {
                "check_in": "2026-11-12",
                "check_out": "2026-11-14",
                "guests": 2,
            }
        },
    )
    correct = {
        "variant": "agent_v1",
        "tool_calls": [
            {
                "name": "check_availability",
                "args": {"check_in": "2026-11-12", "check_out": "2026-11-14", "guests": 2},
            }
        ],
    }
    tool_correct, args_ok, _ = _tool_check(scenario, correct)
    assert tool_correct is True
    assert args_ok is True

    wrong_guests = {
        "variant": "agent_v1",
        "tool_calls": [
            {
                "name": "check_availability",
                "args": {"check_in": "2026-11-12", "check_out": "2026-11-14", "guests": 3},
            }
        ],
    }
    tool_correct, args_ok, _ = _tool_check(scenario, wrong_guests)
    assert tool_correct is True
    assert args_ok is False

    missing = {"variant": "agent_v1", "tool_calls": []}
    tool_correct, args_ok, details = _tool_check(scenario, missing)
    assert tool_correct is False
    assert args_ok is True  # only called tools are checked
    assert details["missing"] == ["check_availability"]

    extra = {
        "variant": "agent_v1",
        "tool_calls": [
            {"name": "check_availability", "args": {}},
            {"name": "get_reservation", "args": {"reservation_id": 1}},
        ],
    }
    tool_correct, _, details = _tool_check(scenario, extra)
    assert tool_correct is False
    assert details["extra"] == ["get_reservation"]

    llm = {"variant": "llm", "tool_calls": []}
    assert _tool_check(scenario, llm)[:2] == (None, None)


def test_source_hit_manual_prefix_and_guide_evidence() -> None:
    manual = _scenario(manual_sections=["4.1"])
    assert _source_check(manual, {"variant": "rag", "retrieved": ["4.1.2"]}, []) is True
    assert _source_check(manual, {"variant": "rag", "retrieved": ["4.2"]}, []) is False
    assert _source_check(manual, {"variant": "llm", "retrieved": []}, []) is None

    guide = _scenario(manual_sections=[], guide_evidence=["wazir khan", "lahore fort"])
    assert (
        _source_check(
            guide,
            {"variant": "agent_v1", "retrieved": ["Lahore > See"]},
            ["The Wazir Khan Mosque and Lahore Fort are in the Walled City."],
        )
        is True
    )
    assert (
        _source_check(
            guide,
            {"variant": "agent_v1", "retrieved": ["Lahore > See"]},
            ["The Wazir Khan Mosque is in the Walled City."],
        )
        is False
    )


def test_unsupported_numbers_and_clock_times() -> None:
    scenario = _scenario(required_facts=[], guest_message="Can I bring 2 guests?")
    unsupported = evaluate_answer(
        scenario,
        "The extra fee is PKR 5,000, a 10% discount, at 9:30 PM.",
        META,
        evidence=["The extra guest fee is PKR 2,000."],
        system_prompt="Prices are in PKR.",
    )
    assert "5000" in unsupported["unsupported_numbers"]
    assert "10%" in unsupported["unsupported_numbers"]
    assert "9:30pm" in unsupported["unsupported_numbers"]
    assert unsupported["hallucination_combined"] is True

    supported = evaluate_answer(
        scenario,
        "The extra fee is PKR 2,000 and check-in is 2:00 PM.",
        META,
        evidence=["The extra guest fee is PKR 2000. Check-in is 2 PM."],
        system_prompt="Prices are in PKR.",
    )
    assert supported["unsupported_numbers"] == []
    assert supported["hallucination_combined"] is False

    year = evaluate_answer(
        scenario,
        "In 2026 the fee is 2,000.",
        META,
        evidence=["fee is 2000"],
    )
    assert "2026" not in year["unsupported_numbers"]


def test_scorer_v2_normalisation_applies_to_answers_and_alternatives() -> None:
    # Ordinal suffixes are stripped on both sides (14th -> 14).
    ordinal = _scenario(required_facts=[["14 november", "2026-11-14"]])
    assert evaluate_answer(ordinal, "You arrive on 14th November.", META)["facts_ok"] is True

    # A missing space before am/pm is removed on both sides (8:00 pm -> 8:00pm).
    clock = _scenario(required_facts=[["8:00 pm", "20:00"]])
    assert evaluate_answer(clock, "It closes at 8:00pm.", META)["facts_ok"] is True
    short_clock = _scenario(required_facts=[["2 pm", "14:00"]])
    assert evaluate_answer(short_clock, "Check-in is 2pm.", META)["facts_ok"] is True

    # En/em dashes act as spaces, so "8:00am-8:00pm" yields both facts.
    dashed = _scenario(required_facts=[["8:00am"], ["8:00pm"]])
    assert evaluate_answer(dashed, "Open 8:00am\u20138:00pm.", META)["facts_ok"] is True
    assert evaluate_answer(dashed, "Open 8:00am\u20148:00pm.", META)["facts_ok"] is True


def test_test_split_reports_are_aggregates_only() -> None:
    report = {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "model": "fake",
        "variants": ["llm"],
        "primary_split": "test",
        "details_included": False,
        "failures": [],
        "manual_review": [],
        "aggregates": {
            "test": {
                "llm": {
                    "overall": {
                        "n": 1,
                        "accuracy": 0.0,
                        "accuracy_ci95": [0.0, 1.0],
                        "tool_correct": {"rate": None},
                        "tool_args_ok": {"rate": None},
                        "hallucination_strict": {"rate": 0.0},
                        "hallucination_combined": {"rate": 0.0},
                        "over_escalation": {"rate": 0.0},
                        "source_hit": {"rate": None},
                        "latency_s": {"median": 1.0, "p95": 1.0, "mean": 1.0},
                        "mean_prompt_tokens": 1.0,
                        "mean_completion_tokens": 1.0,
                        "errors": 0,
                    },
                    "by_category": {},
                    "by_difficulty": {},
                }
            }
        },
        "paired": {"test": {}},
    }
    markdown = render_markdown(report)
    assert "Failure analysis" not in markdown
    assert "Needs manual review" not in markdown
    assert "aggregates only" in markdown


def test_score_result_adds_latency_and_error_fields() -> None:
    scenario = _scenario(required_facts=[], must_escalate_to_host=False)
    result = {
        "variant": "llm",
        "answer": "Hello.",
        "latency_s": 1.5,
        "llm_s": 1.4,
        "tool_s": 0.0,
        "retrieval_s": 0.0,
        "n_llm_calls": 1,
        "prompt_tokens": 10,
        "completion_tokens": 5,
        "error": None,
    }
    row = score_result(scenario, result, META)
    assert row["latency_s"] == 1.5
    assert row["n_llm_calls"] == 1
    assert row["tool_correct"] is None


def test_wilson_interval_and_mcnemar() -> None:
    low, high = _wilson(8, 10)
    assert 0.0 <= low <= 0.8 <= high <= 1.0
    assert _wilson(0, 0) == (None, None)

    rows_a = [{"id": str(index), "accuracy_pass": value} for index, value in enumerate([True, True, False, False])]
    rows_b = [{"id": str(index), "accuracy_pass": value} for index, value in enumerate([False, True, True, False])]
    paired = _mcnemar(rows_a, rows_b)
    assert paired["a_pass_b_fail"] == 1
    assert paired["a_fail_b_pass"] == 1
    assert paired["both_pass"] == 1
    assert paired["both_fail"] == 1
    assert math.isclose(paired["mcnemar_exact_p"], 1.0)
