"""Keeping entry ids out of prose.

Ids belong in `source_entry_ids` and in the IR view, never in a sentence a
person reads. The model writes them into prose anyway, and asking it not to in
the prompt doesn't hold — this has been visible in live output repeatedly. So
it's enforced here, in code, the same way citations are checked rather than
trusted.

Removing the id is the easy half. The hard half is what it leaves behind: a
lead-in ("per entry <id>"), a bracket that's now empty, a list that's lost its
items ("Sources: and."). Each of those reads as a bug too, so they're cleaned
up as well, and a sentence with nothing left to say is dropped entirely.
"""

import re

_UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"

# A bracketed group containing an id goes whole — "(entry <id>)", "[<id>]",
# "(<id>, <id>)" — rather than leaving the brackets stranded, and takes any
# phrase that introduced it with it ("see [<id>]").
_BRACKETED = re.compile(
    rf"\s*\b(?:see|per|from|cf\.?|in)?\s*[(\[][^()\[\]]*{_UUID}[^()\[\]]*[)\]]",
    re.IGNORECASE,
)
# A lead-in phrase belongs to the id it introduces, so it goes with it.
_LEAD_IN = re.compile(
    rf"\b(?:in|per|see|from|of|cf\.?)?\s*"
    rf"(?:entry|entries|id|ids|ref|refs|source|sources)\s*:?\s*{_UUID}",
    re.IGNORECASE,
)
_BARE = re.compile(_UUID)

# What's left once ids are gone can be a sentence with no content: the words
# that only ever glued the citation together.
_FILLER = {
    "and", "or", "also", "see", "per", "from", "of", "in", "at", "the", "this",
    "these", "cf", "source", "sources", "entry", "entries", "id", "ids", "ref",
    "refs", "as", "recorded", "noted", "above", "below",
}


def _tidy(text: str) -> str:
    text = re.sub(r"[(\[]\s*[,;:\s]*[)\]]", "", text)  # brackets left empty
    text = re.sub(r"\s*,\s*(?=[,.;:])", "", text)  # doubled-up commas
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)  # space before punctuation
    text = re.sub(r"([,;:])\s*(?=[.!?])", "", text)  # "Sources: ." -> "Sources."
    text = re.sub(r"([.!?])[ \t]*\.(?=\s|$)", r"\1", text)  # orphaned full stop
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"^[\s,;:.]+", "", text)  # punctuation the removal left leading
    text = text.strip()
    # Whatever now starts the sentence should look like it starts one.
    return text[:1].upper() + text[1:] if text else text


def _is_vacuous(sentence: str) -> bool:
    """True when nothing but citation glue survived."""
    words = re.findall(r"[A-Za-z0-9]+", sentence)
    return not words or all(word.lower() in _FILLER for word in words)


def strip_entry_ids(text: str) -> str:
    """Removes entry ids from prose, along with what they leave behind."""
    # Text with no id in it is left exactly as written — the repairs below are
    # for damage this function caused, and applying them otherwise would mean
    # quietly rewriting prose nobody asked us to touch.
    if not _BARE.search(text):
        return text

    cleaned = _BRACKETED.sub("", text)
    cleaned = _LEAD_IN.sub("", cleaned)
    cleaned = _BARE.sub("", cleaned)
    cleaned = _tidy(cleaned)

    # Sentence by sentence, so one ruined clause doesn't cost the rest.
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    kept = [
        _tidy(sentence) for sentence in sentences if not _is_vacuous(sentence)
    ]
    return " ".join(part for part in kept if part).strip()


def strip_ids_from_content(content: dict) -> dict:
    """Same, over every string in an IR entry's content.

    Proposals are prose too — a statement reading "revises entry <id>" lands in
    the feed and the digest, where there is no citation machinery to excuse it.
    """
    return {
        key: strip_entry_ids(value) if isinstance(value, str) else value
        for key, value in content.items()
    }
