"""A document in; proposed IR changes out.

The same read → propose → submit → merge path a typed sentence runs, because a
document *is* a message — a longer one. What a longer one needs that a sentence
doesn't: cutting into passages that fit in one call, reading those passages, and
reconciling the result with itself before anyone is asked to review it.

Nothing here stores anything, and the file itself is never kept. We take its
text and its name; the bytes go out of scope with the request.
"""

from concurrent.futures import ThreadPoolExecutor

from .. import mistral
from .chunk import Passage, split_passages
from .extract import DocumentError, extract_pages
from .prompt import EXTRACT_SYSTEM_PROMPT, build_extract_prompt
from .reconcile import prepare, reconcile

# Passages are read concurrently — a 20-page spec is a dozen model calls, and
# run one after another that's a minute of somebody watching a spinner. Kept
# low deliberately: this is one person's upload, not a batch job, and there's a
# rate limit on the other end.
MAX_PARALLEL_PASSAGES = 4

__all__ = ["DocumentError", "read_document"]


def read_document(
    filename: str,
    data: bytes,
    existing: list[dict] | None = None,
    model: str = mistral.DEFAULT_MODEL,
) -> dict:
    """Reads a document into proposed changes. Raises DocumentError if we won't
    read the file at all — wrong type, too big, too long, or no text in it."""
    pages = extract_pages(filename, data)
    passages = split_passages(pages, paginated=filename.lower().endswith(".pdf"))

    existing = existing or []
    existing_ids = {entry["id"] for entry in existing}

    def read(passage: Passage) -> tuple[list[dict], int, bool]:
        try:
            result = mistral.complete_json(
                system=EXTRACT_SYSTEM_PROMPT,
                user=build_extract_prompt(
                    passage.text, filename, passage.location, existing
                ),
                model=model,
            )
        except Exception:
            # One passage failing shouldn't lose the other nineteen. It's
            # reported rather than swallowed, so nobody assumes the document
            # was read in full when part of it wasn't.
            return [], 0, True

        raw_operations = (result.data or {}).get("operations") or []
        prepared = [
            prepare(raw, passage, filename, existing_ids) for raw in raw_operations
        ]
        usable = [operation for operation in prepared if operation is not None]
        return usable, len(prepared) - len(usable), False

    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_PASSAGES) as pool:
        # `map` keeps document order, which is the order a reviewer will read
        # the proposals in.
        results = list(pool.map(read, passages))

    operations = [operation for usable, _, _ in results for operation in usable]
    dropped = sum(count for _, count, _ in results)
    failed = sum(1 for _, _, failed_ in results if failed_)

    return {
        "document": filename,
        "passages": len(passages),
        "operations": reconcile(operations, existing, model=model),
        # Both surfaced rather than swallowed: a fact the reader thinks they
        # imported and didn't is the failure mode that matters here.
        "dropped": dropped,
        "failed_passages": failed,
    }
