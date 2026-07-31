"""Is this input a statement of fact or a question?

The two paths diverge completely — one proposes changes to the IR, the other
just reads it — so this runs first and cheap.
"""

import mistral_client

SYSTEM_PROMPT = """Classify a message someone typed into a project workspace.

"statement" - they are reporting something that happened, a decision, a value,
              a plan, or a correction. It adds to what the project knows.
"question"  - they are asking about the project's existing state, or what
              something means for them. It adds nothing; it wants an answer.

A message can be phrased without a question mark and still be a question
("wondering what this means for the filing"), and a rhetorical aside inside a
report does not make the whole message a question.

Return {"kind": "statement"} or {"kind": "question"}."""


def classify(text: str, model: str = "mistral-small-latest") -> str:
    """Returns "statement" or "question". Falls back to "statement" so an
    ambiguous input is at least offered for confirmation rather than swallowed
    as a question and lost."""
    result = mistral_client.complete_json(
        system=SYSTEM_PROMPT, user=text, model=model
    )
    return "question" if result.data.get("kind") == "question" else "statement"
