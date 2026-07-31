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
