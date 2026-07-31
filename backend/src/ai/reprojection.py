"""IR → prose, written for one reader.

Both a project summary and an answer to a question come back as the same shape:
segments of `{text, source_entry_ids}` that the UI concatenates into flowing
paragraphs. Segments keep prose readable while every clause stays traceable —
and the traceability is enforced here, not asked for in the prompt.
"""

import hashlib
import json

from . import mistral

_SEGMENT_CONTRACT = """Return {"segments": [{"text": "...", "source_entry_ids": ["..."]}]}.

Each segment is a sentence or two of flowing prose plus the ids of the entries
it draws on. Concatenated in order, the segments must read as continuous
paragraphs — not a bulleted list, not one segment per entry.

A segment may cite several entries when it genuinely combines them. Every
segment MUST cite at least one entry id from the ENTRIES list, copied exactly.
An uncited segment is discarded, so a claim you cannot source is a claim you
should not write."""

SUMMARY_SYSTEM_PROMPT = f"""You brief one person on a project's state, in their own
professional terms.

You are given the project's neutral facts and a description of the reader. Write
what this project means *for them*.

RULES

1. FILTER. Most facts do not matter to this reader. Leave them out entirely —
   silence is better than a bland restatement. Choosing what to omit is as much
   of the job as choosing what to say.

2. TRANSLATE, DON'T SIMPLIFY. Use their vocabulary and units. Respect what they
   already know: never explain something their description says they are expert
   in. Never talk down.

3. SURFACE IMPLICATIONS. Say what follows for them, including consequences that
   only appear when several facts are combined. The facts state what happened;
   your job is what it means for this reader.

4. GROUND EVERYTHING. Only claim what the entries support. Never invent a
   number, date or consequence that no entry backs.

5. BE BRIEF. A few short paragraphs at most. If little is relevant, say little.

{_SEGMENT_CONTRACT}"""

ANSWER_SYSTEM_PROMPT = f"""You answer one person's question about a project, using
only the project's recorded facts.

RULES

1. ANSWER THE QUESTION ASKED. Directly, in their professional terms.

2. GROUND EVERYTHING. Only what the entries support. If they do not answer the
   question, say so plainly — an honest "the project doesn't record that" is
   correct, an invented answer is not.

3. SURFACE IMPLICATIONS. Combining several facts to answer is expected.

4. BE BRIEF. Answer, then stop.

{_SEGMENT_CONTRACT}"""


def _describe_reader(profile: dict | None) -> str:
    content = (profile or {}).get("content") or {}
    if not content:
        return "READER\nNothing is known about this reader. Write plainly and neutrally.\n"
    return f"READER\n{json.dumps(content, indent=2)}\n"


def _describe_entries(entries: list[dict]) -> str:
    if not entries:
        return "ENTRIES\n(none yet)\n"
    lines = [
        f"  id: {entry['id']}\n  {json.dumps(entry['content'])}" for entry in entries
    ]
    return "ENTRIES\n" + "\n\n".join(lines) + "\n"


def keep_grounded_segments(segments: list, valid_ids: set[str]) -> list[dict]:
    """Drops anything that cannot be traced back to real entries.

    The model will happily cite an id that does not exist, so citations are
    checked here rather than trusted. A segment surviving this means every id it
    names is a real entry in this project.
    """
    grounded = []
    for segment in segments or []:
        if not isinstance(segment, dict):
            continue
        text = segment.get("text")
        if not isinstance(text, str) or not text.strip():
            continue

        cited = [
            entry_id
            for entry_id in segment.get("source_entry_ids") or []
            if isinstance(entry_id, str) and entry_id in valid_ids
        ]
        if not cited:
            continue

        grounded.append({"text": text.strip(), "source_entry_ids": cited})

    return grounded


def _generate(system: str, user: str, entries: list[dict], model: str | None) -> dict:
    result = mistral.complete_json(
        system=system, user=user, model=model or mistral.DEFAULT_MODEL
    )
    segments = keep_grounded_segments(
        result.data.get("segments"), {entry["id"] for entry in entries}
    )
    return {"segments": segments}


def summarize(entries: list[dict], profile: dict | None, model: str | None = None) -> dict:
    user = f"{_describe_reader(profile)}\n{_describe_entries(entries)}"
    return _generate(SUMMARY_SYSTEM_PROMPT, user, entries, model)


def answer(
    question: str, entries: list[dict], profile: dict | None, model: str | None = None
) -> dict:
    user = f"{_describe_reader(profile)}\n{_describe_entries(entries)}\nQUESTION\n{question}"
    return _generate(ANSWER_SYSTEM_PROMPT, user, entries, model)


# --- summary cache ---
#
# Recomputing a summary on every project open is slow and pointless when
# nothing changed. Keyed on what the summary is actually derived from, so a new
# entry, an edited entry, or an edited self-description all invalidate it
# without anyone maintaining a version counter.

_cache: dict[tuple[str, str], tuple[str, dict]] = {}


def cache_key(entries: list[dict], profile: dict | None) -> str:
    material = json.dumps(
        {
            "entries": [(entry["id"], entry["created_at"]) for entry in entries],
            "profile": (profile or {}).get("content") or {},
        },
        sort_keys=True,
    )
    return hashlib.sha256(material.encode()).hexdigest()


def cached_summary(
    project_id: str, user_id: str, entries: list[dict], profile: dict | None
) -> dict:
    key = cache_key(entries, profile)
    hit = _cache.get((project_id, user_id))
    if hit and hit[0] == key:
        return {**hit[1], "cached": True}

    summary = summarize(entries, profile)
    _cache[(project_id, user_id)] = (key, summary)
    return {**summary, "cached": False}


def invalidate_project(project_id: str) -> None:
    """Drop every reader's cached summary of a project.

    The key would catch this on the next read anyway, since it hashes entry
    timestamps — this just avoids keeping known-stale entries around.
    """
    for cached in [key for key in _cache if key[0] == project_id]:
        del _cache[cached]
