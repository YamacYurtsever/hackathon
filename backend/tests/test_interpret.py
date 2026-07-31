"""The prompt's shape, checked without a network call."""

from ai.interpret.prompt import build_prompt
from ai.interpret.validate import clean_operation, parse_operations


def test_empty_project_says_so_explicitly():
    # Left implicit, the model reaches for the id in the prompt's own example
    # and proposes an update against an entry that never existed here.
    prompt = build_prompt("Bumped sampling to 2kHz.")
    assert "KNOWN ENTRIES" in prompt
    assert "none" in prompt
    assert '"create"' in prompt


def test_existing_entries_are_listed_with_ids():
    # Without ids the model can't target an update, so it duplicates the fact.
    prompt = build_prompt(
        "Now 4kHz.",
        existing=[{"id": "abc", "content": {"statement": "It is 2 kHz."}}],
    )
    assert "abc" in prompt
    assert "It is 2 kHz." in prompt


def test_profile_is_included_when_present():
    assert "engineer" in build_prompt("x", profile={"content": {"role": "engineer"}})


def test_update_against_a_missing_entry_is_dropped():
    assert clean_operation(
        {"op": "update", "target_id": "ghost", "content": {"statement": "x"}}, set()
    ) is None


def test_update_against_a_real_entry_survives():
    operation = clean_operation(
        {"op": "update", "target_id": "e1", "content": {"statement": "x"}}, {"e1"}
    )
    assert operation["target_id"] == "e1"


def test_content_without_a_statement_is_dropped():
    assert clean_operation({"op": "create", "content": {"note": "x"}}, set()) is None


def test_reserved_keys_are_stripped():
    operation = clean_operation(
        {"op": "create", "content": {"statement": "x", "id": "nope", "author": "nope"}},
        set(),
    )
    assert operation["content"] == {"statement": "x"}


def test_dropped_operations_are_counted_not_hidden():
    # A silently lost operation is a fact the author thinks they recorded.
    operations, dropped = parse_operations(
        {
            "operations": [
                {"op": "create", "content": {"statement": "good"}},
                {"op": "update", "target_id": "ghost", "content": {"statement": "bad"}},
                "nonsense",
            ]
        },
        set(),
    )
    assert len(operations) == 1
    assert dropped == 2
