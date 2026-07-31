"""IR → prose, written for one reader.

Both a project summary and an answer to a question come back as the same shape:
segments of `{text, source_entry_ids}` that the UI concatenates into flowing
paragraphs. Segments keep prose readable while every clause stays traceable —
and the traceability is enforced here, not asked for in the prompt.
"""

import hashlib
import json

from . import mistral
from .ids import strip_entry_ids

_SEGMENT_CONTRACT = """Return {"segments": [{"text": "...", "source_entry_ids": ["..."]}]}.

Each segment is a sentence or two of flowing prose plus the ids of the entries
it draws on. Concatenated in order, the segments must read as continuous
paragraphs — not a bulleted list, not one segment per entry.

A segment may cite several entries when it genuinely combines them. Every
segment MUST cite at least one entry id from the ENTRIES list, copied exactly.
An uncited segment is discarded, so a claim you cannot source is a claim you
should not write."""

_SEGMENT_CONTRACT_FOR_ANSWERS = """Return {"segments": [{"text": "...", "source_entry_ids": ["..."]}]}.

Each segment is a sentence or two of flowing prose plus the ids of the entries
it draws on. Concatenated in order, the segments must read as continuous
paragraphs — not a bulleted list, not one segment per entry.

A segment may cite several entries when it genuinely combines them, and ids
must be copied exactly from the ENTRIES list. A segment that reasons rather
than reports gets an empty list: that empty list is how the reader is told this
part is your inference. Never cite an entry to lend weight to a claim it does
not actually support."""

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

4. DON'T RECITE. The exact wording of every entry is one click away, in a view
   built for reading the record as it stands — repeating it here wastes the
   only thing you can do that it can't. A segment that reads like an entry with
   the edges smoothed off has done nothing. Interpret, then cite: the citation
   is what points back at the wording, so you don't have to reproduce it.

5. GROUND EVERYTHING. Only claim what the entries support. Never invent a
   number, date or consequence that no entry backs. Interpreting a fact is your
   job; changing what it says is not, and specifics — figures, dates, names —
   must survive interpretation exactly.

6. BE BRIEF. A few short paragraphs at most. If little is relevant, say little.

{_SEGMENT_CONTRACT}"""

ANSWER_SYSTEM_PROMPT = f"""You answer one person's question about a project,
working from the project's recorded facts.

RULES

1. ANSWER THE QUESTION ASKED. Directly, in their professional terms.

2. SEPARATE RECORD FROM REASONING. A segment that states what the project *is*
   must cite the entries it comes from. A segment that reasons — an inference,
   a judgement, a suggestion — cites nothing, and must read as yours rather
   than as something the project recorded.

3. REASONING IS WELCOME. "Who is this product for?" may have no recorded
   answer; inferring one from the entries is the useful reply, not a refusal.
   Say what you're inferring from and how confident it is.

4. NEVER DRESS INFERENCE AS RECORD. Do not state a number, date or decision the
   entries do not contain as though the project had settled it. The line you
   must not cross is asserting a fact, not having an opinion.

5. SURFACE IMPLICATIONS. Combining several facts to answer is expected.

6. DON'T RECITE. Answer the question in your own words. The entries are one
   click away in a view built for reading them; quoting them back is not an
   answer, and the citation already points at the wording.

7. BE BRIEF. Answer, then stop.

{_SEGMENT_CONTRACT_FOR_ANSWERS}"""


WELCOME_SYSTEM_PROMPT = """You greet one person opening a project that has no
recorded facts yet.

You are given only a description of the reader — the project's record is empty.

RULES

1. THERE ARE NO FACTS. Never state, guess or imply anything about what this
   project contains, has decided, or is working on. You do not know, and there
   is nothing to know yet. Inventing one here is the worst thing you could do.

2. SPEAK TO THEIR CONTEXT. Using only their self-description, say what they
   should put in first and what they can expect to get back — in their own
   professional terms. If their description is empty, write plainly instead.

3. BE BRIEF. Two or three sentences. No lists, no headings, no greeting
   boilerplate like "Welcome!".

Return {"text": "..."}."""


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


def keep_grounded_segments(
    segments: list, valid_ids: set[str], require_citation: bool = True
) -> list[dict]:
    """Resolves every citation against real entries, dropping the ones that lie.

    The model will happily cite an id that does not exist, so citations are
    checked here rather than trusted. A segment surviving this means every id it
    names is a real entry in this project.

    `require_citation` is the difference between the two kinds of prose we
    produce. A summary states what the project *is*, so an uncited segment there
    is an unsourced claim and gets dropped. An answer may also reason — "who is
    this product for?" has no recorded answer, and inference from the entries is
    the useful reply — so uncited segments survive there. They simply carry no
    marker, which is what tells the reader it's inference rather than record.
    """
    grounded = []
    for segment in segments or []:
        if not isinstance(segment, dict):
            continue
        text = segment.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        text = strip_entry_ids(text)
        if not text:
            continue

        cited = [
            entry_id
            for entry_id in segment.get("source_entry_ids") or []
            if isinstance(entry_id, str) and entry_id in valid_ids
        ]
        if not cited and require_citation:
            continue

        grounded.append({"text": text.strip(), "source_entry_ids": cited})

    return grounded


def _generate(
    system: str,
    user: str,
    entries: list[dict],
    model: str | None,
    require_citation: bool = True,
) -> dict:
    result = mistral.complete_json(
        system=system, user=user, model=model or mistral.DEFAULT_MODEL
    )
    segments = keep_grounded_segments(
        result.data.get("segments"),
        {entry["id"] for entry in entries},
        require_citation=require_citation,
    )
    return {"segments": segments}


def summarize(entries: list[dict], profile: dict | None, model: str | None = None) -> dict:
    user = f"{_describe_reader(profile)}\n{_describe_entries(entries)}"
    return _generate(SUMMARY_SYSTEM_PROMPT, user, entries, model)


def answer(
    question: str, entries: list[dict], profile: dict | None, model: str | None = None
) -> dict:
    user = f"{_describe_reader(profile)}\n{_describe_entries(entries)}\nQUESTION\n{question}"
    return _generate(
        ANSWER_SYSTEM_PROMPT, user, entries, model, require_citation=False
    )


def welcome(profile: dict | None, model: str | None = None) -> dict:
    """An orienting line for an empty project, shaped by who is reading.

    There is nothing to cite here, so the usual citation check has no purchase —
    the grounding is instead that the only input is the reader's own profile,
    and the prompt forbids saying anything about the project itself.
    """
    result = mistral.complete_json(
        system=WELCOME_SYSTEM_PROMPT,
        user=_describe_reader(profile),
        model=model or mistral.DEFAULT_MODEL,
    )
    text = result.data.get("text")
    return {"text": strip_entry_ids(text) if isinstance(text, str) else ""}


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


# Keyed on the reader alone: an empty project has nothing else to vary on, so
# the same person opening any empty project gets the same orienting line.
_welcome_cache: dict[str, tuple[str, dict]] = {}


def cached_welcome(user_id: str, profile: dict | None) -> dict:
    key = cache_key([], profile)
    hit = _welcome_cache.get(user_id)
    if hit and hit[0] == key:
        return {**hit[1], "cached": True}

    greeting = welcome(profile)
    _welcome_cache[user_id] = (key, greeting)
    return {**greeting, "cached": False}


def invalidate_project(project_id: str) -> None:
    """Drop every reader's cached summary of a project.

    The key would catch this on the next read anyway, since it hashes entry
    timestamps — this just avoids keeping known-stale entries around.
    """
    for cached in [key for key in _cache if key[0] == project_id]:
        del _cache[cached]
