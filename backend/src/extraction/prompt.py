"""Extraction prompt. Ported from the frontend lab in
`frontend/src/lib/extraction/prompt.ts`, extended to emit a changeset
(creates *and* updates) rather than only new entries.
"""

import json

# The IR schema leaves `content` free-form on purpose. This is a *soft*
# convention, not a template: four keys we ask for every time so re-projection
# has something to rely on, plus explicit permission to add whatever else the
# fact needs. Loosen or tighten it here — it is the single place the shape of
# extracted content is decided.
CONTENT_CONVENTION = """Every content object SHOULD carry these four keys:
  "statement"    - one neutral sentence stating the fact. No discipline jargon,
                   no hedging, no audience-specific framing.
  "subject"      - short canonical name of the thing the fact is about
                   (e.g. "ECG sensor sampling rate"). Reuse an existing subject
                   string verbatim when the fact concerns something already known.
  "source_quote" - a VERBATIM span copied from the input text. Must appear in the
                   input character-for-character. This is what the UI shows when a
                   user clicks a citation, so it must be real.
  "certainty"    - one of: "stated" (asserted as fact by the author),
                   "predicted" (expected but not yet observed),
                   "estimated" (approximate figure), or
                   "reported" (relayed from someone/something else).

Beyond those four, add any keys the fact genuinely needs. Suggestions, not rules:
  - quantities as objects with units: {"value": 2000, "unit": "Hz"}
  - changes as "previous" and "current"
  - dates as ISO strings
Do not pad content with keys that carry no information."""

RULES = """You turn a team message into a CHANGESET against a project's neutral
Intermediate Representation (IR). A changeset is a list of operations: facts to
add, and existing facts to revise.

RULES

1. ATOMIC. One operation per fact. A message stating three things produces three
   operations. Never bundle unrelated facts into one.

2. NEUTRAL, NOT SIMPLIFIED. Strip framing that belongs to the author's
   discipline, but keep every bit of technical precision. "2 kHz" stays "2 kHz";
   it does not become "a higher rate". You are removing perspective, not detail.

3. GROUND EVERYTHING. Every operation needs a source_quote that appears verbatim
   in the input. If you cannot quote it, you may not claim it.

4. NEVER INVENT. If the message implies something without specifying it — a
   value, a date, a mechanism — do NOT fill it in. Put it in "unresolved" with
   the quote that raised the question. An unresolved item is a success, not a
   failure.

5. ADD NO PRECISION THE INPUT LACKS. Never sharpen a value beyond what was
   written. "14 March" has no year, so do not emit "2024-03-14". "a couple of
   weeks" is not "14 days". If it is not in the message, it is unresolved.

6. SAY WHAT WAS SAID, NOT WHAT IT MEANS. Do not extract consequences,
   downstream impacts, or implications for other disciplines. A prediction the
   author made is a fact about their prediction (certainty "predicted"); a
   consequence you worked out yourself is not extractable. Something else
   computes those later.

7. UPDATE, DON'T DUPLICATE. If a fact revises something in KNOWN ENTRIES —
   a value changed, a figure was corrected, a plan was superseded — emit an
   "update" naming that entry's id, with the full replacement content. Only emit
   "create" when the fact is genuinely new. A contradicting duplicate is a bug.

8. NO ENVELOPE FIELDS. Never emit "id", "author" or "created_at" inside content
   — those are assigned outside the model.

OUTPUT
Return a single JSON object:
{
  "operations": [
    { "op": "create", "content": { ... } },
    { "op": "update", "target_id": "<id from KNOWN ENTRIES>", "content": { ... } }
  ],
  "unresolved": [ { "quote": "...", "issue": "..." } ]
}
Both keys are required; use [] when empty."""

EXAMPLE = """EXAMPLE

KNOWN ENTRIES
  - id: e-17 | subject: "ECG sensor sampling rate" | The ECG sensor sampling rate is 2 kHz.

Input: "Actually we settled on 4kHz, and added a debounce filter — should cut false positives."

Output:
{
  "operations": [
    {
      "op": "update",
      "target_id": "e-17",
      "content": {
        "statement": "The ECG sensor sampling rate was set to 4 kHz.",
        "subject": "ECG sensor sampling rate",
        "source_quote": "Actually we settled on 4kHz",
        "certainty": "stated",
        "previous": { "value": 2000, "unit": "Hz" },
        "current": { "value": 4000, "unit": "Hz" }
      }
    },
    {
      "op": "create",
      "content": {
        "statement": "A debounce filter was added to the detection signal chain.",
        "subject": "detection signal chain",
        "source_quote": "added a debounce filter",
        "certainty": "stated",
        "change_type": "addition"
      }
    },
    {
      "op": "create",
      "content": {
        "statement": "The author expects these changes to reduce the false positive rate.",
        "subject": "false positive rate",
        "source_quote": "should cut false positives",
        "certainty": "predicted",
        "expected_direction": "decrease"
      }
    }
  ],
  "unresolved": [
    {
      "quote": "added a debounce filter",
      "issue": "No time constant, window length, or position in the signal chain was given."
    },
    {
      "quote": "should cut false positives",
      "issue": "No magnitude given and no measurement taken; recorded as a prediction, not as a new false positive rate."
    }
  ]
}

Note the first operation revises e-17 instead of adding a second, contradicting
sampling-rate fact. Note the third: the author's prediction is recorded as a
prediction. Note also what is absent — nothing about validation studies, filings
or schedules. Those are consequences, and consequences are not extracted."""

EXTRACTION_SYSTEM_PROMPT = f"{RULES}\n\n{CONTENT_CONVENTION}\n\n{EXAMPLE}"


def _describe_profile(profile: dict | None) -> str:
    if not profile:
        return ""
    return f"""AUTHOR CONTEXT
The message was written by this person. Use it only to resolve shorthand and
jargon — it must NOT colour the extracted facts, which stay neutral.
{json.dumps(profile.get("content", {}), indent=2)}

"""


def _describe_existing(entries: list[dict]) -> str:
    """Existing entries with ids, so the model can target updates instead of
    duplicating a fact it should be revising."""
    if not entries:
        return ""

    lines = []
    for entry in entries:
        content = entry.get("content", {})
        subject = content.get("subject", "")
        statement = content.get("statement", "")
        lines.append(f'  - id: {entry["id"]} | subject: "{subject}" | {statement}')

    return """KNOWN ENTRIES
Facts already in the project. Reuse a subject string verbatim when a new fact is
about the same thing, and emit an "update" naming the id when a fact revises one.
{}

""".format("\n".join(lines))


def build_extraction_prompt(
    text: str, profile: dict | None = None, existing: list[dict] | None = None
) -> str:
    return (
        f"{_describe_profile(profile)}"
        f"{_describe_existing(existing or [])}"
        f'MESSAGE TO EXTRACT\n"""\n{text}\n"""'
    )


def build_repair_prompt(original: str, rejected: list[dict]) -> str:
    """Second-chance prompt: hand the model its own failures and ask for a fix."""
    listed = "\n".join(
        f"{index}. {json.dumps(item['content'])}\n   problems: {'; '.join(item['problems'])}"
        for index, item in enumerate(rejected, start=1)
    )

    return f"""{original}

YOUR PREVIOUS ATTEMPT HAD REJECTED OPERATIONS
{listed}

Re-extract the message from scratch. The most common failure is a source_quote
that is not a character-for-character span of the input — copy and paste it,
never paraphrase or reconstruct it. Drop any fact you cannot quote."""
