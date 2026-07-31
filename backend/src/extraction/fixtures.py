"""Adversarial test corpus — each fixture targets one failure mode.

Needs a live model, so these drive `eval_extraction.py` rather than the unit
tests, which stay offline.
"""

# Soft expectations: eyeball aids, not hard assertions. A model is allowed to
# reasonably disagree about how many facts a sentence holds.
FIXTURES = [
    {
        "id": "canonical",
        "label": "Canonical demo message",
        "author": "engineer",
        "text": "Bumped sampling rate to 2kHz, added debounce filter, should cut false positives.",
        "min_operations": 3,
        "mentions": ["sampling rate", "debounce", "false positive"],
        "expect_unresolved": True,
        "note": "The scenario from CLAUDE.md. Must NOT extract validation/510(k)/timeline consequences.",
    },
    {
        "id": "consequence-bait",
        "label": "Consequence bait",
        "author": "biologist",
        "text": (
            "Ran the FP study on the old build last week, got 4.2%. Obviously that "
            "number is dead now that the firmware changed, and legal will want to know."
        ),
        "min_operations": 2,
        "mentions": ["4.2", "study"],
        "expect_unresolved": True,
        "note": "The author states a consequence themselves — that IS extractable as their claim. But the extractor must not add filing consequences of its own.",
    },
    {
        "id": "vague",
        "label": "Vague, nothing to pin down",
        "author": "business",
        "text": "Talked to the vendor, they think the enclosure might slip a bit but nothing serious.",
        "min_operations": 1,
        "mentions": ["enclosure"],
        "expect_unresolved": True,
        "note": "No dates, no magnitude. Almost everything should land in unresolved.",
    },
    {
        "id": "dense",
        "label": "Dense multi-fact",
        "author": "lawyer",
        "text": (
            "Submission went out 14 March. Predicate is the CardioTrack CT-200. FDA has "
            "90 days to respond, so we should hear by mid-June at the latest."
        ),
        "min_operations": 3,
        "mentions": ["submission", "predicate", "90"],
        "expect_unresolved": False,
        "note": 'Tests atomicity, and the year trap: "14 March" has no year, so a "2024-03-14" must be rejected.',
    },
    {
        "id": "quote-trap",
        "label": "Quote trap (jargon + numbers)",
        "author": "engineer",
        "text": (
            "Moved the AFE gain from 6x to 12x and re-tuned the 0.5–40Hz bandpass. "
            "Noise floor looks better on the bench."
        ),
        "min_operations": 3,
        "mentions": ["gain", "bandpass", "noise"],
        "expect_unresolved": True,
        "note": 'Models like to normalise "0.5–40Hz" or "6x" when quoting. The verbatim check should catch it.',
    },
    {
        "id": "revision",
        "label": "Revises an existing fact",
        "author": "engineer",
        "text": "Actually we settled on 4kHz in the end, not 2.",
        "min_operations": 1,
        "mentions": ["4"],
        "expect_unresolved": False,
        "needs_existing": True,
        "note": "Must emit an update against the seeded sampling-rate entry, not a second contradicting create.",
    },
]
