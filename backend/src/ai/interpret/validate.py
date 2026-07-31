"""Checks on what the model returned. Pure functions, no network."""

# Envelope fields the model must never author. Stripped, not rejected.
RESERVED_KEYS = ("id", "author", "created_at")


def clean_operation(raw: object, existing_ids: set[str]) -> dict | None:
    """Returns a usable operation, or None if it can't be trusted.

    An update naming an entry that isn't there is dropped rather than applied,
    since it would otherwise land as a create — inventing a fact nobody proposed.
    """
    if not isinstance(raw, dict):
        return None

    content = raw.get("content")
    if not isinstance(content, dict):
        return None
    if not isinstance(content.get("statement"), str) or not content["statement"].strip():
        return None

    op = raw.get("op", "create")
    if op not in ("create", "update"):
        return None

    operation = {
        "op": op,
        "content": {k: v for k, v in content.items() if k not in RESERVED_KEYS},
    }

    if op == "update":
        target_id = raw.get("target_id")
        if target_id not in existing_ids:
            return None
        operation["target_id"] = target_id

    return operation


def parse_operations(data: object, existing_ids: set[str]) -> tuple[list[dict], int]:
    """Coerces a raw model response into operations.

    Returns the usable ones and a count of what was thrown away, so a caller can
    tell the author something went missing instead of quietly losing a fact.
    """
    if not isinstance(data, dict):
        raise ValueError("Model response was not a JSON object.")

    raw_operations = data.get("operations") or []
    operations = [
        operation
        for operation in (clean_operation(raw, existing_ids) for raw in raw_operations)
        if operation is not None
    ]
    return operations, len(raw_operations) - len(operations)
