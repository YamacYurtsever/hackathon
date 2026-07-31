"""Turning many passages' worth of proposals back into one document's facts.

Two jobs. First the cheap one, in code: the overlap between passages means the
same sentence is genuinely read twice, so an identical statement extracted twice
is collapsed without asking anyone. Then the expensive one, with a model: the
same fact stated in an abstract, a table and an appendix is worded differently
each time, and only a reader can tell that those three are one fact.

Also here: the check that a proposal's quote is actually in the passage it
claims to come from. Provenance nobody verified is decoration, and the model
will paraphrase a quote given the chance — so it's checked in code, the same way
citations are.
"""

import re

from .. import mistral
from ..interpret.validate import clean_operation
from .prompt import (
    RECONCILE_SYSTEM_PROMPT,
    build_reconcile_prompt,
)

_WHITESPACE = re.compile(r"\s+")


def _normalise(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip().lower()


def quote_from(raw: object, passage_text: str) -> str | None:
    """The proposal's quote, if it really is in the passage.

    Whitespace is normalised on both sides because a PDF's line breaks land
    wherever the page ended, and a quote spanning two lines is verbatim in every
    sense that matters. Anything else — a tidied, stitched or invented quote —
    returns None, and the caller keeps the fact without a quote rather than
    showing a reviewer a passage that doesn't exist.
    """
    if not isinstance(raw, str) or not raw.strip():
        return None
    if _normalise(raw) not in _normalise(passage_text):
        return None
    return raw.strip()


def prepare(raw: object, passage, document_name: str, existing_ids: set[str]) -> dict | None:
    """One raw proposal from a passage, checked and given its provenance."""
    operation = clean_operation(raw, existing_ids)
    if operation is None:
        return None

    quote = quote_from((raw or {}).get("source_quote"), passage.text)
    operation["provenance"] = {
        "document": document_name,
        "locations": [passage.location],
        # Absent when the model paraphrased instead of copying. The reviewer
        # sees where the fact came from either way; they just don't get a quote
        # we can't stand behind.
        **({"quote": quote} if quote else {}),
    }
    return operation


def collapse_identical(operations: list[dict]) -> list[dict]:
    """Drops proposals that are word-for-word repeats of an earlier one.

    Passages overlap on purpose, so this fires on every document — no model call
    needed to see that the same sentence was read twice.
    """
    kept: list[dict] = []
    seen: dict[tuple, int] = {}

    for operation in operations:
        key = (
            operation.get("target_id") or "",
            _normalise(str(operation["content"].get("statement", ""))),
        )
        if key in seen:
            merge_provenance(kept[seen[key]], operation)
            continue
        seen[key] = len(kept)
        kept.append(operation)

    return kept


def merge_provenance(keeper: dict, duplicate: dict) -> None:
    """Folds a dropped duplicate's location into the one being kept.

    A fact stated on page 2 and again on page 9 is one fact with two places it
    was found, and a reviewer checking it deserves both.
    """
    into = keeper.setdefault("provenance", {}).setdefault("locations", [])
    for location in duplicate.get("provenance", {}).get("locations", []):
        if location not in into:
            into.append(location)


def reconcile(
    operations: list[dict],
    existing: list[dict] | None = None,
    model: str = mistral.DEFAULT_MODEL,
) -> list[dict]:
    """Collapses restatements of one fact, and points restatements of an
    existing fact at the entry they revise.

    A failure here is not worth failing the whole import over: the fallback is
    the un-reconciled list, which a person is about to review anyway. Duplicates
    that survive cost a reviewer a moment; a lost import costs them the document.
    """
    operations = collapse_identical(operations)
    if len(operations) < 2:
        return operations

    try:
        result = mistral.complete_json(
            system=RECONCILE_SYSTEM_PROMPT,
            user=build_reconcile_prompt(operations, existing),
            model=model,
        )
    except Exception:
        return operations

    return _apply(operations, result.data, {entry["id"] for entry in existing or []})


def _apply(operations: list[dict], data: object, existing_ids: set[str]) -> list[dict]:
    """Applies the reconciler's verdict, ignoring anything that doesn't check out.

    Every index is validated against the list we actually sent: a model naming
    proposal 30 of 12 would otherwise drop a real fact or crash the import.
    """
    if not isinstance(data, dict):
        return operations

    dropped: dict[int, int] = {}
    for group in data.get("duplicates") or []:
        if not isinstance(group, dict):
            continue
        keep = group.get("keep")
        if not _is_index(keep, operations):
            continue
        for index in group.get("drop") or []:
            # Not itself, not something already dropped, and not a proposal
            # that another group is keeping.
            if _is_index(index, operations) and index != keep and index not in dropped:
                dropped[index] = keep

    for index, keeper in dropped.items():
        merge_provenance(operations[keeper], operations[index])

    for revision in data.get("revisions") or []:
        if not isinstance(revision, dict):
            continue
        index = revision.get("proposal")
        entry_id = revision.get("entry_id")
        if not _is_index(index, operations) or index in dropped:
            continue
        # An id that isn't in this project would land as a create at merge time,
        # inventing a fact nobody proposed. Same check as everywhere else.
        if entry_id not in existing_ids:
            continue
        operations[index]["op"] = "update"
        operations[index]["target_id"] = entry_id

    return [
        operation
        for index, operation in enumerate(operations)
        if index not in dropped
    ]


def _is_index(value: object, operations: list) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value < len(operations)
