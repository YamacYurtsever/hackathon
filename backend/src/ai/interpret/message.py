"""A team message in; proposed IR changes and an answer out.

One call does both, because a message can be either or both — "we settled on
4kHz, does that move the filing?" is a fact and a question at once, and asking
a classifier to pick one loses half of it.

Nothing here mints ids or timestamps. Interpretation proposes; an entry gets an
identity only once an admin approves the request built from an operation.
"""

from .. import mistral

from .prompt import SYSTEM_PROMPT, build_prompt
from .validate import parse_operations


def interpret_message(
    text: str,
    profile: dict | None = None,
    existing: list[dict] | None = None,
    model: str = mistral.DEFAULT_MODEL,
) -> dict:
    source = text.strip()
    if not source:
        raise ValueError("Nothing to interpret — the message is empty.")

    existing = existing or []
    result = mistral.complete_json(
        system=SYSTEM_PROMPT,
        user=build_prompt(source, profile, existing),
        model=model,
    )

    operations, dropped = parse_operations(
        result.data, {entry["id"] for entry in existing}
    )
    answer = result.data.get("answer")

    return {
        "operations": operations,
        "answer": answer if isinstance(answer, str) and answer.strip() else None,
        # Surfaced rather than swallowed: a silently dropped operation is a fact
        # the author thinks they recorded and didn't.
        "dropped": dropped,
    }
