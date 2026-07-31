import pytest

from extraction.prompt import build_extraction_prompt
from extraction.validate import (
    find_fabricated_dates,
    is_verbatim,
    parse_model_response,
    strip_reserved_keys,
    validate_content,
    validate_operation,
)

SOURCE = "Bumped sampling rate to 2kHz, added debounce filter, should cut false positives."


def content(**overrides) -> dict:
    base = {
        "statement": "The sampling rate was raised to 2 kHz.",
        "subject": "ECG sensor sampling rate",
        "source_quote": "Bumped sampling rate to 2kHz",
        "certainty": "stated",
    }
    base.update(overrides)
    return base


# --- verbatim quoting: the grounding guardrail ---


def test_verbatim_accepts_exact_span():
    assert is_verbatim("added debounce filter", SOURCE)


def test_verbatim_tolerates_case_whitespace_and_curly_quotes():
    assert is_verbatim("BUMPED   sampling\nrate", SOURCE)
    assert is_verbatim("don't", "Don’t ship it yet")


def test_verbatim_rejects_paraphrase():
    # The model reconstructing a quote instead of copying it is the failure
    # this whole check exists to catch.
    assert not is_verbatim("raised the sampling rate to 2kHz", SOURCE)


def test_verbatim_rejects_empty_quote():
    assert not is_verbatim("   ", SOURCE)


# --- content validation ---


def test_valid_content_has_no_problems():
    assert validate_content(content(), SOURCE) == []


def test_empty_content_is_rejected():
    assert validate_content({}, SOURCE) == ["content is empty"]


@pytest.mark.parametrize("field", ["statement", "subject", "certainty", "source_quote"])
def test_each_required_field_is_reported_when_missing(field):
    broken = content()
    del broken[field]
    problems = validate_content(broken, SOURCE)
    assert any(field in problem for problem in problems)


def test_unknown_certainty_is_rejected():
    problems = validate_content(content(certainty="probably"), SOURCE)
    assert any("certainty" in problem for problem in problems)


def test_fabricated_quote_is_rejected():
    problems = validate_content(content(source_quote="we doubled the sample rate"), SOURCE)
    assert any("not verbatim" in problem for problem in problems)


# --- fabricated precision (the bug the frontend lab flagged) ---


def test_invented_year_is_rejected():
    # "14 March" in the input became "2024-03-14" in the output — the model
    # adding precision that was never there.
    problems = find_fabricated_dates({"date": "2024-03-14"}, "Freezing the design on 14 March")
    assert len(problems) == 1
    assert "2024" in problems[0]


def test_year_present_in_the_input_is_fine():
    assert find_fabricated_dates({"date": "2024-03-14"}, "Freezing on 14 March 2024") == []


def test_quantities_are_not_mistaken_for_years():
    # 2000 Hz must not read as the year 2000 — this false positive would break
    # the canonical demo message.
    assert find_fabricated_dates({"current": {"value": 2000, "unit": "Hz"}}, SOURCE) == []


def test_nested_dates_are_checked():
    problems = find_fabricated_dates(
        {"schedule": {"review_date": "2019-01-02"}}, "review it next week"
    )
    assert len(problems) == 1


# --- changeset operations ---


def test_create_operation_is_valid():
    operation = {"op": "create", "content": content()}
    assert validate_operation(operation, SOURCE, set()) == []


def test_update_operation_needs_a_target():
    operation = {"op": "update", "content": content()}
    problems = validate_operation(operation, SOURCE, {"e-17"})
    assert any("target_id" in problem for problem in problems)


def test_update_targeting_a_real_entry_is_valid():
    operation = {"op": "update", "target_id": "e-17", "content": content()}
    assert validate_operation(operation, SOURCE, {"e-17"}) == []


def test_update_targeting_an_unknown_entry_is_rejected():
    # Otherwise it would silently apply as a create, inventing a fact nobody
    # proposed.
    operation = {"op": "update", "target_id": "ghost", "content": content()}
    problems = validate_operation(operation, SOURCE, {"e-17"})
    assert any("not an entry in this project" in problem for problem in problems)


def test_unknown_op_is_rejected():
    operation = {"op": "delete", "content": content()}
    problems = validate_operation(operation, SOURCE, set())
    assert any('"op"' in problem for problem in problems)


# --- response parsing ---


def test_reserved_keys_are_stripped():
    cleaned = strip_reserved_keys({"id": "x", "author": "y", "created_at": "z", "subject": "s"})
    assert cleaned == {"subject": "s"}


def test_parse_extracts_operations_and_unresolved():
    parsed = parse_model_response(
        {
            "operations": [
                {"op": "create", "content": {"subject": "a"}},
                {"op": "update", "target_id": "e-1", "content": {"subject": "b"}},
            ],
            "unresolved": [{"quote": "q", "issue": "vague"}],
        }
    )
    assert [op["op"] for op in parsed["operations"]] == ["create", "update"]
    assert parsed["operations"][1]["target_id"] == "e-1"
    assert parsed["unresolved"] == [{"quote": "q", "issue": "vague"}]


def test_parse_drops_malformed_operations():
    parsed = parse_model_response(
        {"operations": ["nonsense", {"op": "create"}, {"op": "create", "content": {"a": 1}}]}
    )
    assert len(parsed["operations"]) == 1


def test_parse_defaults_missing_keys_to_empty():
    assert parse_model_response({}) == {"operations": [], "unresolved": []}


def test_parse_rejects_non_object():
    with pytest.raises(ValueError):
        parse_model_response(["not", "an", "object"])


# --- prompt assembly ---


def test_prompt_lists_existing_entries_with_ids():
    # Without ids in the prompt the model cannot target an update, and would
    # duplicate the fact instead of revising it.
    prompt = build_extraction_prompt(
        SOURCE,
        profile=None,
        existing=[{"id": "e-17", "content": {"subject": "sampling rate", "statement": "It is 2 kHz."}}],
    )
    assert "e-17" in prompt
    assert "sampling rate" in prompt


def test_prompt_includes_author_profile():
    prompt = build_extraction_prompt(SOURCE, profile={"content": {"role": "engineer"}})
    assert "engineer" in prompt


def test_prompt_omits_empty_sections():
    prompt = build_extraction_prompt(SOURCE)
    assert "KNOWN ENTRIES" not in prompt
    assert "AUTHOR CONTEXT" not in prompt
