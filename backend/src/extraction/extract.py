"""NL → changeset orchestration: call, validate, one repair retry, assemble.

Unlike the frontend lab this ports from, nothing here mints ids or timestamps.
Extraction proposes; an entry only gets an identity once an admin approves the
request built from this changeset.
"""

import mistral_client

from .prompt import (
    EXTRACTION_SYSTEM_PROMPT,
    build_extraction_prompt,
    build_repair_prompt,
)
from .validate import parse_model_response, validate_operation

MAX_ATTEMPTS = 2


def extract_changeset(
    text: str,
    profile: dict | None = None,
    existing: list[dict] | None = None,
    model: str = mistral_client.DEFAULT_MODEL,
) -> dict:
    """Runs extraction, validates every operation against the grounding rules,
    and gives the model exactly one chance to repair its failures before
    dropping them.

    Invalid operations are never returned as if they were good: they land in
    `rejected` so a caller can show what was thrown away and why.
    """
    source = text.strip()
    if not source:
        raise ValueError("Nothing to extract — the message is empty.")

    existing = existing or []
    existing_ids = {entry["id"] for entry in existing}
    base_prompt = build_extraction_prompt(source, profile, existing)

    accepted: list[dict] = []
    rejected: list[dict] = []
    unresolved: list[dict] = []
    attempts = 0
    latency_ms = 0
    prompt_tokens = 0
    completion_tokens = 0
    raw = ""

    for attempt in range(MAX_ATTEMPTS):
        prompt = base_prompt if attempt == 0 else build_repair_prompt(base_prompt, rejected)

        result = mistral_client.complete_json(
            system=EXTRACTION_SYSTEM_PROMPT, user=prompt, model=model
        )

        attempts += 1
        latency_ms += result.latency_ms
        prompt_tokens += result.prompt_tokens or 0
        completion_tokens += result.completion_tokens or 0
        raw = result.raw

        parsed = parse_model_response(result.data)

        accepted = []
        rejected = []
        for operation in parsed["operations"]:
            problems = validate_operation(operation, source, existing_ids)
            if problems:
                rejected.append({**operation, "problems": problems})
            else:
                accepted.append(operation)
        unresolved = parsed["unresolved"]

        if not rejected:
            break

    return {
        "operations": accepted,
        "unresolved": unresolved,
        "rejected": rejected,
        "diagnostics": {
            "attempts": attempts,
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens or None,
            "completion_tokens": completion_tokens or None,
            "model": model,
            "raw": raw,
        },
    }
