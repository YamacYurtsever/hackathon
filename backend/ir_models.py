from typing import Any, Literal

from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    kind: Literal["document", "message"] = Field(
        description="Whether the supporting quote came from a document or message.",
    )
    page: int | None = Field(
        ge=1,
        description="One-indexed source page, or null for a natural-language message.",
    )
    quote: str = Field(
        min_length=3,
        max_length=500,
        description="A short verbatim quote from the source supporting the fact.",
    )


class ExtractedFact(BaseModel):
    statement: str = Field(
        min_length=3,
        max_length=1200,
        description="One atomic, neutral fact explicitly supported by the input.",
    )
    category: Literal[
        "context",
        "change",
        "decision",
        "requirement",
        "action",
        "risk",
        "metric",
        "constraint",
    ]
    entities: list[str] = Field(
        description="Named people, teams, systems, products, or concepts in the fact.",
    )
    source: SourceReference
    confidence: Literal["high", "medium", "low"]


class ExtractionBatch(BaseModel):
    entries: list[ExtractedFact] = Field(
        description="Atomic facts extracted from the supplied input.",
    )


class ClaimDraft(BaseModel):
    text: str = Field(
        min_length=3,
        max_length=1800,
        description="A useful re-projected claim for the viewer.",
    )
    entry_id: str = Field(
        description="The exact IR entry ID that grounds this claim.",
    )
    grounding_paths: list[str] = Field(
        min_length=1,
        description=(
            "Paths within the entry that support the claim, such as "
            "'content.statement' or 'content.entities'."
        ),
    )
    is_implication: bool = Field(
        description="True when the claim surfaces an implication for the viewer.",
    )


class ReprojectionBatch(BaseModel):
    claims: list[ClaimDraft] = Field(
        description="Grounded claims tailored to the supplied viewer profile.",
    )


class GroundedAnswerDraft(BaseModel):
    answer: str = Field(
        min_length=1,
        max_length=5000,
        description="A direct answer based only on the supplied IR entries.",
    )
    citation_ids: list[str] = Field(
        description="IDs of every IR entry that supports the answer.",
    )
    insufficient_evidence: bool = Field(
        description="True when the IR does not contain enough information to answer.",
    )


class ConflictDraft(BaseModel):
    title: str = Field(
        min_length=3,
        max_length=160,
        description="A short, neutral description of the detected conflict.",
    )
    summary: str = Field(
        min_length=3,
        max_length=1200,
        description="How the cited IR entries are incompatible.",
    )
    conflict_type: Literal[
        "contradiction",
        "requirement_violation",
        "decision_mismatch",
        "constraint_violation",
    ]
    required_expertise: str = Field(
        min_length=3,
        max_length=300,
        description="The expertise needed to independently review a solution.",
    )
    conflicting_entry_ids: list[str] = Field(
        min_length=2,
        description="Exact IDs of the mutually incompatible IR entries.",
    )
    reviewer_ids: list[str] = Field(
        min_length=1,
        description="Exact project member IDs best qualified to review.",
    )
    participant_ids: list[str] = Field(
        min_length=1,
        description="Exact project member IDs who should resolve the conflict.",
    )
    confidence: Literal["high"] = Field(
        description="Only high-confidence conflicts may create an issue.",
    )


class ConflictBatch(BaseModel):
    conflicts: list[ConflictDraft] = Field(
        description=(
            "High-confidence conflicts introduced or exposed by the new IR entries."
        ),
    )


def read_content_path(entry: dict[str, Any], path: str) -> Any | None:
    if not path.startswith("content."):
        return None
    value: Any = entry
    for segment in path.split("."):
        if not isinstance(value, dict) or segment not in value:
            return None
        value = value[segment]
    return value
