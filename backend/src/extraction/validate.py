"""Grounding checks. Pure functions, no network.

Ported from `frontend/src/lib/extraction/validate.ts`, plus operation-level
validation for the changeset model and a check for fabricated date precision —
a gap the lab's README flagged after seeing "14 March" become "2024-03-14".
"""

import re

CERTAINTY_VALUES = ("stated", "predicted", "estimated", "reported")

# Envelope fields the model must never author. Stripped, not rejected.
RESERVED_KEYS = ("id", "author", "created_at")

_ISO_DATE = re.compile(r"\b(\d{4})-\d{2}-\d{2}\b")
_YEAR = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")


def normalize_for_quote_match(text: str) -> str:
    """Whitespace, case and punctuation-style differences are not hallucinations —
    models routinely straighten curly quotes or re-wrap lines. Everything else is."""
    text = text.lower()
    text = re.sub(r"[‘’‛]", "'", text)
    text = re.sub(r"[“”]", '"', text)
    text = re.sub(r"[‐-―]", "-", text)
    return re.sub(r"\s+", " ", text).strip()


def is_verbatim(quote: str, source_text: str) -> bool:
    """The mechanical form of the grounding guardrail: a quote must really be in
    the source."""
    needle = normalize_for_quote_match(quote)
    if not needle:
        return False
    return needle in normalize_for_quote_match(source_text)


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _walk_strings(value: object, key: str = ""):
    """Yield (key, string) for every string in a nested content object."""
    if isinstance(value, str):
        yield key, value
    elif isinstance(value, dict):
        for child_key, child in value.items():
            yield from _walk_strings(child, child_key)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_strings(child, key)


def find_fabricated_dates(content: dict, source_text: str) -> list[str]:
    """Catch date precision the input never contained.

    Only looks at ISO dates and date-ish keys on purpose: a bare four-digit
    number is usually a quantity, not a year — "2000" in {"value": 2000,
    "unit": "Hz"} must not be mistaken for one.
    """
    problems = []
    normalized_source = normalize_for_quote_match(source_text)

    for key, text in _walk_strings(content):
        is_date_key = "date" in key.lower() or "year" in key.lower()
        years = _ISO_DATE.findall(text) or (_YEAR.findall(text) if is_date_key else [])
        for year in years:
            if year not in normalized_source:
                problems.append(
                    f'"{key}" contains the year {year}, which does not appear in the input'
                )

    return problems


def strip_reserved_keys(content: dict) -> dict:
    """Drops envelope fields the model should not have authored."""
    return {key: value for key, value in content.items() if key not in RESERVED_KEYS}


def validate_content(content: dict, source_text: str) -> list[str]:
    """Validates one content object against the soft convention. Returns the
    problems found; an empty list means it is usable."""
    if not content:
        return ["content is empty"]

    problems = []

    if not _is_non_empty_string(content.get("statement")):
        problems.append('missing "statement"')
    if not _is_non_empty_string(content.get("subject")):
        problems.append('missing "subject"')

    certainty = content.get("certainty")
    if not _is_non_empty_string(certainty):
        problems.append('missing "certainty"')
    elif certainty not in CERTAINTY_VALUES:
        problems.append(
            f'"certainty" is "{certainty}", expected one of {", ".join(CERTAINTY_VALUES)}'
        )

    quote = content.get("source_quote")
    if not _is_non_empty_string(quote):
        problems.append('missing "source_quote" — an ungrounded fact cannot be shown')
    elif not is_verbatim(quote, source_text):
        problems.append(f'"source_quote" is not verbatim in the input: {quote!r}')

    problems.extend(find_fabricated_dates(content, source_text))

    return problems


def validate_operation(
    operation: dict, source_text: str, existing_ids: set[str]
) -> list[str]:
    """Validates a changeset operation: the op itself, then its content."""
    problems = []

    op = operation.get("op")
    if op not in ("create", "update"):
        problems.append(f'"op" is {op!r}, expected "create" or "update"')

    if op == "update":
        target_id = operation.get("target_id")
        if not _is_non_empty_string(target_id):
            problems.append('"update" is missing "target_id"')
        elif target_id not in existing_ids:
            # An update naming an entry that isn't there would silently become a
            # create, inventing a fact nobody proposed.
            problems.append(f'"target_id" {target_id!r} is not an entry in this project')

    problems.extend(validate_content(operation.get("content") or {}, source_text))
    return problems


def parse_model_response(data: object) -> dict:
    """Coerces a raw model response into operations, tolerating minor shape drift."""
    if not isinstance(data, dict):
        raise ValueError("Model response was not a JSON object.")

    operations = []
    for raw in data.get("operations") or []:
        if not isinstance(raw, dict):
            continue
        content = raw.get("content")
        if not isinstance(content, dict):
            continue
        operation = {
            "op": raw.get("op", "create"),
            "content": strip_reserved_keys(content),
        }
        if _is_non_empty_string(raw.get("target_id")):
            operation["target_id"] = raw["target_id"]
        operations.append(operation)

    unresolved = []
    for raw in data.get("unresolved") or []:
        if not isinstance(raw, dict):
            continue
        if _is_non_empty_string(raw.get("issue")):
            unresolved.append(
                {
                    "quote": raw["quote"] if _is_non_empty_string(raw.get("quote")) else "",
                    "issue": raw["issue"],
                }
            )

    return {"operations": operations, "unresolved": unresolved}
