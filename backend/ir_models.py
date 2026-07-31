from typing import Literal

from pydantic import BaseModel, Field


class SourceReference(BaseModel):
    page: int = Field(
        ge=1,
        description="One-indexed page number where the fact appears.",
    )
    quote: str = Field(
        min_length=3,
        max_length=500,
        description="A short verbatim quote from that page supporting the fact.",
    )


class ExtractedFact(BaseModel):
    statement: str = Field(
        min_length=3,
        max_length=1200,
        description="One atomic, neutral fact explicitly supported by the document.",
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
        description="Atomic facts extracted from the supplied pages.",
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
