"""Entry ids must never reach a sentence a person reads.

Each case here is a shape the model actually produced. Stripping the id is the
easy half; these mostly pin down what it leaves behind.
"""

import pytest

from ai.ids import strip_entry_ids, strip_ids_from_content

ID = "24f65462-b121-4afd-93ba-2f46ae51410d"
OTHER = "0ca6a59c-7170-4569-95f7-d6ece85b6aaf"


@pytest.mark.parametrize(
    "text,expected",
    [
        (f"The rate ({ID}) is fixed.", "The rate is fixed."),
        (f"The rate (entry {ID}) is fixed.", "The rate is fixed."),
        (f"The filter (id: {ID}) matters.", "The filter matters."),
        (f"The rate ({ID}, {OTHER}) is fixed.", "The rate is fixed."),
        # A lead-in belongs to the id it introduces.
        (f"Per entry {ID}, sampling is 1 kHz.", "Sampling is 1 kHz."),
        (f"Sampling is 1 kHz, as recorded in entry {ID}.", "Sampling is 1 kHz, as recorded."),
        # A sentence that was only ever a citation goes entirely.
        (f"The rate is fixed. Sources: {ID}.", "The rate is fixed."),
        (f"Sources: {ID} and {OTHER}.", ""),
    ],
)
def test_ids_and_their_wreckage_are_removed(text, expected):
    assert strip_entry_ids(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "No ids here at all — 2 kHz and a 510(k) filing.",
        "Budget is $2.4M (through year-end) and the pilot is 14 March.",
        "Version 1.2.3-alpha and code ABCD-1234 stay put.",
        "lowercase stays lowercase",
    ],
)
def test_prose_without_ids_is_untouched(text):
    """The repairs are for damage this function causes. Text it didn't touch
    must come back byte-identical, or we're silently rewriting people's words."""
    assert strip_entry_ids(text) == text


def test_proposals_are_cleaned_too():
    """Proposals land in the feed and the digest, where there is no citation
    machinery to excuse an id sitting in a sentence."""
    content = {"statement": f"Sampling is 2 kHz (revises {ID}).", "rate": "2 kHz"}

    assert strip_ids_from_content(content) == {
        "statement": "Sampling is 2 kHz.",
        "rate": "2 kHz",
    }


@pytest.mark.parametrize(
    "text",
    [
        f"Revises entry {ID}: sampling is 2 kHz.",
        f"{ID}",
        f"See {ID} — and also {OTHER}!",
        f"a{ID}b",
    ],
)
def test_no_id_ever_survives(text):
    """Tidying the wreckage is best-effort; removing the id is not. Whatever
    the shape, nothing that looks like an entry id may reach the reader."""
    assert ID not in strip_entry_ids(text)
    assert OTHER not in strip_entry_ids(text)


def test_non_string_values_survive():
    assert strip_ids_from_content({"statement": "x", "n": 3, "ok": True}) == {
        "statement": "x",
        "n": 3,
        "ok": True,
    }
