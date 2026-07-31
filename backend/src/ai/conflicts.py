"""Finding two facts in the record that can't both be true.

This is not the update path. An update is someone saying "that changed" —
the old wording is meant to go. A conflict is two people asserting things that
can't both hold, where neither is claiming to overwrite the other, and picking
a winner would settle by accident what nobody has actually settled.

Detection runs where the IR changes, against what was already there. The model
proposes pairs; which entries exist is checked here, because a pair naming an
id that isn't in this project is not a conflict, it's a hallucination.
"""

import json

from . import mistral

SYSTEM_PROMPT = """You compare newly recorded facts about a project against the
facts already recorded, and report only genuine contradictions.

A contradiction is two statements that cannot both be true of the same project
at the same time. "Sampling is 2 kHz" and "sampling is 1 kHz" contradict.
"Sampling is 2 kHz" and "the filter is second-order" do not.

RULES

1. BE STRICT. Most pairs are unrelated, and most related pairs are compatible.
   A false alarm costs someone a real decision, so report nothing rather than
   something plausible.

2. DIFFERENT SUBJECTS NEVER CONFLICT. Two facts about different components,
   documents or dates are not in tension just because they sit near each other.

3. NOT EVERY CHANGE IS A CONTRADICTION. A fact that supersedes another — a
   value that was updated, a date that moved — was a revision, and the record
   already reflects it. Only report the case where both are asserted as true.

4. SAY WHY, IN ONE SENTENCE, naming what can't hold at once. Whoever has to
   settle it reads this line first.

OUTPUT
{"conflicts": [{"a": "<id>", "b": "<id>", "reason": "..."}]}

Ids must be copied exactly from the facts given. Return an empty list when
nothing genuinely contradicts — that is the common answer."""


def _describe(entries: list[dict], heading: str) -> str:
    lines = [
        f"  id: {entry['id']}\n  {json.dumps(entry['content'])}" for entry in entries
    ]
    return f"{heading}\n" + ("\n\n".join(lines) if lines else "  (none)") + "\n"


def find_conflicts(
    landed: list[dict], existing: list[dict], model: str | None = None
) -> list[dict]:
    """Pairs of contradicting entry ids, checked against the entries given.

    `landed` is what just changed; `existing` is everything else in the project.
    Comparing only against what changed keeps this one call per merge rather
    than every pair on every read — a contradiction between two untouched
    entries was found when the second of them landed.
    """
    if not landed or not existing:
        return []

    known = {entry["id"] for entry in landed} | {entry["id"] for entry in existing}

    try:
        result = mistral.complete_json(
            system=SYSTEM_PROMPT,
            user=(
                f"{_describe(landed, 'JUST RECORDED')}\n"
                f"{_describe(existing, 'ALREADY RECORDED')}"
            ),
            model=model or mistral.DEFAULT_MODEL,
        )
    except Exception:
        # A missed conflict is bad; a merge that fails because the check was
        # rate-limited is worse. The next merge looks again.
        return []

    found = []
    for pair in result.data.get("conflicts") or []:
        if not isinstance(pair, dict):
            continue
        a, b = pair.get("a"), pair.get("b")
        # Both ends have to be real entries of this project, and a fact cannot
        # contradict itself.
        if a not in known or b not in known or a == b:
            continue
        reason = pair.get("reason")
        found.append(
            {
                "a": a,
                "b": b,
                "reason": reason.strip()
                if isinstance(reason, str) and reason.strip()
                else "These two can't both be true.",
            }
        )
    return found
