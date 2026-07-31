from types import SimpleNamespace

from ir_models import ExtractedFact
from mistral_service import MistralDocumentService


def test_grounding_removes_quotes_that_are_not_on_the_cited_page():
    facts = [
        ExtractedFact.model_validate(
            {
                "statement": "The sampling rate is 2 kHz.",
                "category": "metric",
                    "entities": ["sampling rate"],
                    "source": {
                        "kind": "document",
                        "page": 1,
                    "quote": "The sampling rate is 2 kHz.",
                },
                "confidence": "high",
            }
        ),
        ExtractedFact.model_validate(
            {
                "statement": "The device is approved.",
                "category": "decision",
                    "entities": ["device"],
                    "source": {
                        "kind": "document",
                        "page": 1,
                    "quote": "The device is already approved.",
                },
                "confidence": "high",
            }
        ),
    ]
    pages = [{"page": 1, "markdown": "The sampling rate is 2 kHz."}]

    grounded = MistralDocumentService._ground_facts(facts, pages)

    assert [fact.statement for fact in grounded] == [
        "The sampling rate is 2 kHz."
    ]


def test_answer_fails_closed_when_model_invents_citation_id():
    parsed = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    parsed={
                        "answer": "The launch is tomorrow.",
                        "citation_ids": ["ir_invented"],
                        "insufficient_evidence": False,
                    }
                )
            )
        ]
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(parse=lambda **_kwargs: parsed),
    )
    service = MistralDocumentService("", client=client)
    entries = [
        {
            "id": "ir_real",
            "content": {
                "statement": "The launch date is undecided.",
                "source": {"page": 2, "quote": "launch date is undecided"},
            },
        }
    ]

    answer = service.answer_question("When is launch?", entries)

    assert answer["insufficient_evidence"] is True
    assert answer["citations"] == []
    assert "couldn't find enough grounded information" in answer["answer"]


def test_api_error_message_explains_invalid_key():
    error = RuntimeError("hidden upstream error")
    error.status_code = 401

    message = MistralDocumentService._api_error_message(error, "read this file")

    assert "401 Unauthorized" in message
    assert "new inference API key" in message
    assert "backend/.env" in message


def test_reprojection_drops_claims_with_unknown_ids_or_paths():
    parsed = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    parsed={
                        "claims": [
                            {
                                "text": "Review the firmware baseline.",
                                "entry_id": "ir_real",
                                "grounding_paths": ["content.statement"],
                                "is_implication": True,
                            },
                            {
                                "text": "Invented claim.",
                                "entry_id": "ir_unknown",
                                "grounding_paths": ["content.statement"],
                                "is_implication": False,
                            },
                            {
                                "text": "Invalid path.",
                                "entry_id": "ir_real",
                                "grounding_paths": ["content.does_not_exist"],
                                "is_implication": False,
                            },
                        ]
                    }
                )
            )
        ]
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(parse=lambda **_kwargs: parsed),
    )
    service = MistralDocumentService("", client=client)
    entries = [
        {
            "id": "ir_real",
            "author": "user_engineer",
            "created_at": "2026-07-31T00:00:00+00:00",
            "content": {"statement": "The debounce filter was enabled."},
        }
    ]

    claims = service.reproject_entries(entries, {"expertise": "Firmware"})

    assert len(claims) == 1
    assert claims[0]["entry_id"] == "ir_real"
    assert claims[0]["grounding"][0]["path"] == "content.statement"


def test_conflict_detection_requires_grounding_and_independent_reviewers():
    parsed = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    parsed={
                        "conflicts": [
                            {
                                "title": "Sampling baseline conflict",
                                "summary": "The new rate violates the accepted rate.",
                                "conflict_type": "requirement_violation",
                                "required_expertise": "Signal validation",
                                "conflicting_entry_ids": ["ir_old", "ir_new"],
                                "reviewer_ids": ["user_author"],
                                "participant_ids": ["user_author"],
                                "confidence": "high",
                            },
                            {
                                "title": "Invented conflict",
                                "summary": "This cites evidence that was not supplied.",
                                "conflict_type": "contradiction",
                                "required_expertise": "Firmware",
                                "conflicting_entry_ids": ["ir_new", "ir_invented"],
                                "reviewer_ids": ["user_expert"],
                                "participant_ids": ["user_author"],
                                "confidence": "high",
                            },
                        ]
                    }
                )
            )
        ]
    )
    client = SimpleNamespace(
        chat=SimpleNamespace(parse=lambda **_kwargs: parsed),
    )
    service = MistralDocumentService("", client=client)
    existing = [
        {
            "id": "ir_old",
            "author": "user_owner",
            "content": {"statement": "The accepted rate is 1 kHz."},
        }
    ]
    new = [
        {
            "id": "ir_new",
            "author": "user_author",
            "content": {"statement": "The rate changed to 2 kHz."},
        }
    ]
    members = [
        {"id": "user_owner", "content": {"expertise": "Firmware"}},
        {"id": "user_author", "content": {"expertise": "Firmware"}},
        {"id": "user_expert", "content": {"expertise": "Signal validation"}},
    ]

    conflicts = service.detect_conflicts(new, existing, members, [])

    assert len(conflicts) == 1
    assert conflicts[0]["source_entry_ids"] == ["ir_old", "ir_new"]
    assert conflicts[0]["participant_ids"] == ["user_author", "user_owner"]
    assert conflicts[0]["reviewer_ids"] == ["user_expert"]
