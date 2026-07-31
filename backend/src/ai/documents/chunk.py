"""A document, cut into passages small enough to read a fact out of.

Two things matter here and they pull against each other. A passage has to be
small, or extraction skims it. And a fact must never be *only* half-present in
a passage — "sampling was raised to" in one and "2 kHz" in the next extracts as
two fragments, which is worse than missing it entirely. So passages overlap:
the tail of one is repeated at the head of the next, and a fact straddling the
cut is whole in at least one of them.

Cuts are made at paragraph breaks first and sentence ends second, because those
are where a document itself says a thought has finished. Cutting mid-sentence
is the failure this module exists to avoid.
"""

import re
from dataclasses import dataclass

TARGET_CHARS = 2500
# The tail carried into the next passage. Comfortably longer than a sentence,
# so a fact spanning a cut survives whole on the far side.
OVERLAP_CHARS = 400

_PARAGRAPH_END = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class Block:
    """A paragraph, and where in the document it was."""

    text: str
    page: int
    start_line: int
    end_line: int


@dataclass(frozen=True)
class Passage:
    """What one extraction call reads, and the citation it can claim."""

    text: str
    location: str


def split_passages(
    pages: list[str],
    paginated: bool,
    target: int = TARGET_CHARS,
    overlap: int = OVERLAP_CHARS,
) -> list[Passage]:
    """Packs a document's paragraphs into overlapping passages."""
    blocks = _blocks(pages, target)
    passages: list[Passage] = []

    current: list[Block] = []
    size = 0
    # Whether `current` holds anything beyond the tail carried over from the
    # last passage. Without this, a long block arriving right after a cut would
    # emit a passage made only of repeated text.
    has_new_text = False

    for block in blocks:
        if has_new_text and size + len(block.text) > target:
            passages.append(_passage(current, paginated))
            current = _carry(current, overlap)
            size = sum(len(carried.text) for carried in current)
            has_new_text = False

        current.append(block)
        size += len(block.text)
        has_new_text = True

    if has_new_text:
        passages.append(_passage(current, paginated))
    return passages


def _blocks(pages: list[str], target: int) -> list[Block]:
    """Every paragraph in the document, in order, with its position."""
    blocks: list[Block] = []
    line = 1

    for page_number, page in enumerate(pages, start=1):
        lines = page.split("\n")
        buffer: list[str] = []
        start = line

        for offset, text in enumerate(lines):
            if text.strip():
                if not buffer:
                    start = line + offset
                buffer.append(text)
            elif buffer:
                blocks.extend(
                    _fit("\n".join(buffer), page_number, start, line + offset - 1, target)
                )
                buffer = []

        if buffer:
            blocks.extend(
                _fit("\n".join(buffer), page_number, start, line + len(lines) - 1, target)
            )
        line += len(lines)

    return blocks


def _fit(text: str, page: int, start_line: int, end_line: int, target: int) -> list[Block]:
    """Splits a paragraph longer than a whole passage, at sentence ends.

    A wall-of-text paragraph is common in extracted PDF prose, where the
    original line breaks are gone. Splitting it at sentence ends is the closest
    thing to a paragraph break that's left.
    """
    if len(text) <= target:
        return [Block(text, page, start_line, end_line)]

    pieces: list[Block] = []
    current = ""
    for sentence in _PARAGRAPH_END.split(text):
        if current and len(current) + len(sentence) > target:
            pieces.append(Block(current.strip(), page, start_line, end_line))
            current = ""
        current = f"{current} {sentence}" if current else sentence

    # A single sentence longer than a whole passage has no sentence end to cut
    # at, so it stays intact and overruns rather than being severed mid-clause.
    if current.strip():
        pieces.append(Block(current.strip(), page, start_line, end_line))
    return pieces


def _carry(blocks: list[Block], overlap: int) -> list[Block]:
    """The tail of a passage, repeated at the head of the next one."""
    if not blocks:
        return []

    last = blocks[-1]
    if len(last.text) <= overlap:
        return [last]

    # Whole sentences only: a half-sentence carried over reads as a fragment
    # and is exactly the thing the overlap exists to prevent.
    tail = ""
    for sentence in reversed(_PARAGRAPH_END.split(last.text)):
        if tail and len(tail) + len(sentence) > overlap:
            break
        tail = f"{sentence} {tail}" if tail else sentence

    return [Block(tail.strip() or last.text[-overlap:], last.page, last.start_line, last.end_line)]


def _passage(blocks: list[Block], paginated: bool) -> Passage:
    text = "\n\n".join(block.text for block in blocks)
    return Passage(text=text, location=_location(blocks, paginated))


def _location(blocks: list[Block], paginated: bool) -> str:
    """Where a fact from this passage should say it came from."""
    if paginated:
        first, last = blocks[0].page, blocks[-1].page
        return f"page {first}" if first == last else f"pages {first}–{last}"

    first, last = blocks[0].start_line, blocks[-1].end_line
    return f"line {first}" if first == last else f"lines {first}–{last}"
