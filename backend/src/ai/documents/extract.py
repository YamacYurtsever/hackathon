"""Bytes in, readable text out — with the ceilings applied before any of it.

A document is refused up front or it is read in full. Discovering halfway
through a 300-page PDF that it was never going to be affordable is a cost and
latency incident; refusing it in the first millisecond is a message.

Nothing here keeps the file. We take its text and its name, and the bytes are
dropped on the way out of the request — this is a fact store, not a document
store.
"""

import io
import os

# Read as text, split as paragraphs. Anything else — a .docx, a spreadsheet,
# an image — decodes into garbage that extracts into confident nonsense, which
# is worse than a refusal.
PLAIN_SUFFIXES = (".txt", ".text", ".md", ".markdown")
PDF_SUFFIXES = (".pdf",)

MAX_BYTES = 5 * 1024 * 1024
MAX_PAGES = 40
# Roughly a 40-page PDF's worth of prose. A plain-text file has no page count
# to refuse on, so it gets refused on length instead.
MAX_CHARS = 120_000


class DocumentError(Exception):
    """A document we won't read, with the reason to show the person who sent it."""


def extract_pages(filename: str, data: bytes) -> list[str]:
    """The document's text, one string per page.

    A PDF has real pages; a text file is one long page. Keeping the same shape
    for both means the chunker doesn't care which it got, and a fact from a PDF
    can still say which page it came from.
    """
    if len(data) > MAX_BYTES:
        raise DocumentError(
            f"That file is {len(data) // (1024 * 1024)} MB. "
            f"The limit is {MAX_BYTES // (1024 * 1024)} MB."
        )

    suffix = os.path.splitext(filename or "")[1].lower()
    if suffix in PDF_SUFFIXES:
        pages = _pdf_pages(data)
    elif suffix in PLAIN_SUFFIXES:
        pages = [_decode(data)]
    else:
        raise DocumentError(
            f"{suffix or 'That file type'} can't be read. Send a PDF, markdown, "
            "or plain text file."
        )

    total = sum(len(page) for page in pages)
    if total > MAX_CHARS:
        raise DocumentError(
            f"That document is about {total // 1000}k characters. "
            f"The limit is {MAX_CHARS // 1000}k — send the relevant section."
        )
    # Stripped, not raw: a file of blank lines has no text in it either, and
    # passing one on produces a passage the reader can only hallucinate from.
    if not any(page.strip() for page in pages):
        raise DocumentError(
            "There's no text in that file. A scanned PDF is an image of text, "
            "not text — we can't read one."
        )

    return pages


def _decode(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        # Latin-1 decodes any byte sequence, so this never raises — but a file
        # that isn't text at all still turns into mojibake, which is why the
        # suffix check above is the real guard.
        return data.decode("latin-1")


def _pdf_pages(data: bytes) -> list[str]:
    try:
        from pypdf import PdfReader
    except ImportError:  # pragma: no cover - dependency is in requirements.txt
        raise DocumentError("PDF support isn't installed on this server.")

    try:
        reader = PdfReader(io.BytesIO(data))
        page_count = len(reader.pages)
    except Exception:
        raise DocumentError("That PDF couldn't be opened — it may be corrupt.")

    # Checked before extracting, not after: page count is in the trailer, so
    # refusing costs nothing while extracting 300 pages costs real seconds.
    if page_count > MAX_PAGES:
        raise DocumentError(
            f"That PDF is {page_count} pages. The limit is {MAX_PAGES} — "
            "send the section that matters."
        )

    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            # One unreadable page shouldn't lose the other thirty-nine.
            pages.append("")
    return pages
