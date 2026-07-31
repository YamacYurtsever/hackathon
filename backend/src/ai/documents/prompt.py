"""Prompts for reading a document: one per passage, then one to reconcile.

The extraction rules are deliberately the same rules a typed message gets — a
document is a longer message, not a different kind of input. What's new is the
quote requirement and the instruction to ignore a document's furniture.
"""

EXTRACT_SYSTEM_PROMPT = """You read one passage of a project document and return
the facts it states, as proposed changes to the project's neutral Intermediate
Representation (IR).

RULES

1. ATOMIC. One operation per fact. A passage stating six things produces six
   operations.

2. NEUTRAL, NOT SIMPLIFIED. Strip the document's framing, keep every bit of
   technical precision. "2 kHz" stays "2 kHz"; it does not become "a higher
   rate". You are removing perspective, not detail.

3. NEVER INVENT. Do not fill in a value, date or mechanism the passage did not
   give, and never sharpen one beyond what was written. If the passage is vague,
   the fact is vague.

4. SAY WHAT WAS SAID, NOT WHAT IT MEANS. Do not extract consequences or
   implications for other disciplines. Something else computes those later.

5. UPDATE, DON'T DUPLICATE. If the passage revises something in KNOWN ENTRIES,
   emit an "update" naming that entry's id, with the full replacement content.
   Only "create" when the fact is genuinely new to the project.

6. IGNORE THE FURNITURE. Page numbers, running headers and footers, tables of
   contents, revision-history tables, legal boilerplate, figure captions with no
   content of their own, bibliographies. They are how a document is assembled,
   not what it says. A passage that is entirely furniture returns no operations,
   and that is a correct answer.

7. QUOTE VERBATIM. Every operation carries "source_quote": the sentence or
   clause from THIS PASSAGE that states the fact, copied character for
   character. Do not paraphrase it, do not tidy it, do not stitch two distant
   sentences together. A quote that cannot be found in the passage gets the
   whole operation discarded, so copy rather than reconstruct.

8. THE PASSAGE MAY BEGIN MID-DOCUMENT. Its first lines may repeat the end of
   the previous passage — extract what it states regardless; duplicates are
   reconciled later. But do not extract a fact that is cut off at the passage's
   edge and never completed.

CONTENT
Every content object needs a "statement": one neutral sentence stating the fact.
Add any other keys the fact genuinely needs — quantities with units, "previous"
and "current" for changes, whatever fits. Never emit "id", "author" or
"created_at".

OUTPUT
{
  "operations": [
    { "op": "create", "content": { "statement": "..." }, "source_quote": "..." },
    { "op": "update", "target_id": "<id from KNOWN ENTRIES>",
      "content": { ... }, "source_quote": "..." }
  ]
}"""


RECONCILE_SYSTEM_PROMPT = """A document has been read passage by passage, so the
same fact stated in an abstract, a table and an appendix has been proposed
several times over. You collapse those repeats.

You are given the proposals, numbered, and the project's existing facts. Return:

1. "duplicates" — groups of proposals that state THE SAME FACT. Keep the
   fullest, most precise one; drop the rest. Two facts about the same subject
   are not duplicates: "sampling is 2 kHz" and "sampling is configurable"
   are different facts and both survive. A later proposal that CONTRADICTS an
   earlier one is not a duplicate either — leave both and let a person decide.

2. "revisions" — proposals that restate or revise something already in EXISTING
   ENTRIES. These become updates to that entry instead of new facts.

When in doubt, leave a proposal alone. Merging two distinct facts loses one of
them permanently; a duplicate that survives is merely reviewed twice.

OUTPUT
{
  "duplicates": [{ "keep": 3, "drop": [7, 12] }],
  "revisions": [{ "proposal": 5, "entry_id": "<id from EXISTING ENTRIES>" }]
}

Both lists may be empty. Every number must be a proposal number you were given."""


def build_extract_prompt(
    passage_text: str,
    document_name: str,
    location: str,
    existing: list[dict] | None = None,
) -> str:
    parts = [f'DOCUMENT\n"{document_name}", {location}\n']

    # Stated even when empty: without it the model reaches for an id it saw in
    # its own instructions and proposes an update against an entry that was
    # never in this project.
    if existing:
        lines = "\n".join(
            f"  - id: {entry['id']} | {entry['content'].get('statement', '')}"
            for entry in existing
        )
        parts.append(f"KNOWN ENTRIES\n{lines}\n")
    else:
        parts.append(
            "KNOWN ENTRIES\n"
            "  (none — this project has no facts yet)\n"
            'Every operation must be a "create".\n'
        )

    parts.append(f'PASSAGE\n"""\n{passage_text}\n"""')
    return "\n".join(parts)


def build_reconcile_prompt(operations: list[dict], existing: list[dict] | None) -> str:
    proposals = "\n".join(
        f"  {index}. [{operation['op']}] {operation['content'].get('statement', '')}"
        for index, operation in enumerate(operations)
    )
    parts = [f"PROPOSALS\n{proposals}\n"]

    if existing:
        lines = "\n".join(
            f"  - id: {entry['id']} | {entry['content'].get('statement', '')}"
            for entry in existing
        )
        parts.append(f"EXISTING ENTRIES\n{lines}")
    else:
        parts.append(
            "EXISTING ENTRIES\n"
            '  (none — this project has no facts yet, so "revisions" must be empty)'
        )

    return "\n".join(parts)
