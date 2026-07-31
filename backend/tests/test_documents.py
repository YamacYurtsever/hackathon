"""Reading a document into proposals. The model is stubbed throughout — what's
under test is the chunking, the quote check and the reconciliation, none of
which are the model's judgement.
"""

import io

import pytest

from ai import conflicts as conflict_detection
from ai import mistral
from ai.documents import read_document
from ai.documents.chunk import split_passages
from ai.documents.extract import DocumentError, extract_pages
from ai.documents.prompt import RECONCILE_SYSTEM_PROMPT
from ai.documents.reconcile import collapse_identical, quote_from, reconcile
from data import store

DOC = "spec.md"


def stub_model(monkeypatch, extract=None, reconcile=None):
    """Stubs both model calls at their single shared patch point.

    `ai.documents` and `ai.documents.reconcile` each do `from .. import mistral`,
    so they hold the *same* module object — there is no per-module attribute to
    patch, and patching one patches both. The system prompt is what tells the
    two calls apart, so that's what this dispatches on.
    """

    def dispatch(system, user, model=None):
        handler = reconcile if system == RECONCILE_SYSTEM_PROMPT else extract
        if handler is None:
            raise AssertionError(
                "unexpected model call: "
                f"{'reconcile' if system == RECONCILE_SYSTEM_PROMPT else 'extract'}"
            )
        return handler(system=system, user=user)

    monkeypatch.setattr(mistral, "complete_json", dispatch)


def op(statement: str, quote: str | None = None, **extra) -> dict:
    """A raw proposal, shaped the way a passage extraction returns one."""
    return {
        "op": "create",
        "content": {"statement": statement},
        "source_quote": quote if quote is not None else statement,
        **extra,
    }


def prepared(statement: str, location: str = "page 1", **extra) -> dict:
    """A proposal that has already been through `prepare` — provenance attached."""
    return {
        "op": "create",
        "content": {"statement": statement},
        "provenance": {"document": DOC, "locations": [location]},
        **extra,
    }


# --- extraction: what we'll read, and what we refuse ---


def test_plain_text_is_one_page():
    assert extract_pages("notes.txt", b"Sampling is 2 kHz.") == ["Sampling is 2 kHz."]


def test_unsupported_types_are_refused_with_a_reason():
    with pytest.raises(DocumentError) as refusal:
        extract_pages("protocol.docx", b"PK\x03\x04 anything")

    # Extracting garbage out of a .docx would produce confident nonsense — the
    # refusal has to name what it will read instead.
    assert ".docx" in str(refusal.value)
    assert "PDF" in str(refusal.value)


def test_an_empty_document_is_refused():
    with pytest.raises(DocumentError):
        extract_pages("blank.md", b"   \n  \n")


def test_an_oversized_file_is_refused_before_anything_reads_it():
    with pytest.raises(DocumentError) as refusal:
        extract_pages("huge.txt", b"x" * (6 * 1024 * 1024))

    assert "MB" in str(refusal.value)


def test_a_long_document_is_refused_on_length():
    with pytest.raises(DocumentError) as refusal:
        extract_pages("long.md", ("A fact. " * 20_000).encode())

    assert "characters" in str(refusal.value)


# --- chunking: a cut must not fall through the middle of a fact ---


def test_a_fact_spanning_a_cut_survives_whole_in_one_passage():
    """The failure this module exists to prevent: "sampling was raised to" in
    one passage and "2 kHz" in the next extracts as two fragments."""
    fact = "The ECG sensor sampling rate was raised from 1 kHz to 2 kHz."
    filler = "Background prose that carries no fact at all. " * 12
    text = "\n\n".join([filler, filler, fact, filler, filler])

    passages = split_passages([text], paginated=False, target=600, overlap=200)

    assert len(passages) > 1
    assert any(fact in passage.text for passage in passages)


def test_consecutive_passages_overlap():
    text = "\n\n".join(f"Paragraph number {n} states a fact." for n in range(40))

    passages = split_passages([text], paginated=False, target=400, overlap=120)

    assert len(passages) > 2
    # The tail of one passage is repeated at the head of the next, which is what
    # gives a straddling fact somewhere to survive. The carry is whole blocks —
    # a half-sentence tail is exactly what the overlap exists to prevent — so
    # this checks the last block reappears, not a fixed number of characters.
    for earlier, later in zip(passages, passages[1:]):
        tail = earlier.text.split("\n\n")[-1]
        assert later.text.startswith(tail)


def test_passages_stay_near_the_target_size():
    text = "\n\n".join(f"Paragraph {n} says something." for n in range(60))

    passages = split_passages([text], paginated=False, target=400, overlap=100)

    # Overlap plus a whole paragraph can push a passage past the target; what
    # matters is that nothing balloons to many times it.
    assert all(len(passage.text) < 800 for passage in passages)


def test_a_paragraph_longer_than_a_passage_is_cut_at_sentence_ends():
    text = " ".join(f"Sentence {n} states a fact." for n in range(60))

    passages = split_passages([text], paginated=False, target=300, overlap=80)

    assert len(passages) > 1
    for passage in passages:
        assert passage.text.strip().endswith(".")


def test_pdf_passages_are_located_by_page():
    passages = split_passages(
        ["First page prose.", "Second page prose."], paginated=True, target=20, overlap=5
    )

    # A location describes the text the passage actually holds. The second one
    # opens with the tail carried over from page 1, so it spans both — saying
    # "page 2" would misattribute any fact drawn from that carried tail.
    assert [passage.location for passage in passages] == ["page 1", "pages 1–2"]


def test_a_passage_within_one_page_names_only_that_page():
    passages = split_passages(["Only page prose."], paginated=True)

    assert [passage.location for passage in passages] == ["page 1"]


def test_text_passages_are_located_by_line():
    passages = split_passages(["Line one.\n\nLine three."], paginated=False)

    assert passages[0].location == "lines 1–3"


# --- provenance: a quote nobody checked is decoration ---


def test_a_quote_must_actually_be_in_the_passage():
    passage = "The sampling rate is 2 kHz."

    assert quote_from("The sampling rate is 2 kHz.", passage) == "The sampling rate is 2 kHz."
    # Paraphrased rather than copied — the fact survives, the quote doesn't.
    assert quote_from("Sampling runs at 2 kHz.", passage) is None
    assert quote_from("", passage) is None


def test_a_quote_broken_across_lines_is_still_verbatim():
    """A PDF's line breaks land wherever the page ended, so a quote spanning
    two lines is verbatim in every sense that matters."""
    passage = "The sampling rate\nis 2 kHz."

    assert quote_from("The sampling rate is 2 kHz.", passage) == "The sampling rate is 2 kHz."


# --- reconciliation: one fact, however many times it was stated ---


def test_a_fact_restated_word_for_word_collapses_without_a_model():
    """Passages overlap on purpose, so the same sentence is genuinely read twice."""
    collapsed = collapse_identical(
        [
            prepared("Sampling is 2 kHz.", "page 1"),
            prepared("Sampling is 2 kHz.", "page 4"),
            prepared("The filter is a debounce filter.", "page 4"),
        ]
    )

    assert len(collapsed) == 2
    # One fact, both places it was found — a reviewer checking it deserves both.
    assert collapsed[0]["provenance"]["locations"] == ["page 1", "page 4"]


def test_a_fact_reworded_across_chunks_collapses_to_one_proposal(monkeypatch):
    """The same fact in an abstract and an appendix is worded differently each
    time, so only a reader can tell those are one fact."""
    stub_model(
        monkeypatch,
        reconcile=lambda **_: _Result(
            {"duplicates": [{"keep": 0, "drop": [1]}], "revisions": []}
        ),
    )

    reconciled = reconcile(
        [
            prepared("The sampling rate is 2 kHz.", "page 1"),
            prepared("Sampling runs at 2 kHz.", "page 9"),
        ]
    )

    assert [operation["content"]["statement"] for operation in reconciled] == [
        "The sampling rate is 2 kHz."
    ]
    assert reconciled[0]["provenance"]["locations"] == ["page 1", "page 9"]


def test_a_document_restating_a_known_fact_becomes_an_update(monkeypatch):
    stub_model(monkeypatch, reconcile=lambda **_: _Result(
            {"duplicates": [], "revisions": [{"proposal": 1, "entry_id": "e-17"}]}
        ))
    existing = [{"id": "e-17", "content": {"statement": "Sampling is 1 kHz."}}]

    reconciled = reconcile(
        [prepared("A debounce filter was added."), prepared("Sampling is 2 kHz.")],
        existing,
    )

    assert reconciled[1]["op"] == "update"
    assert reconciled[1]["target_id"] == "e-17"


def test_a_revision_naming_an_unknown_entry_is_ignored(monkeypatch):
    """It would land as a create at merge time, inventing a fact nobody proposed."""
    stub_model(monkeypatch, reconcile=lambda **_: _Result(
            {"duplicates": [], "revisions": [{"proposal": 0, "entry_id": "ghost"}]}
        ))

    reconciled = reconcile([prepared("One."), prepared("Two.")], [])

    assert reconciled[0]["op"] == "create"
    assert "target_id" not in reconciled[0]


def test_an_out_of_range_index_doesnt_drop_a_real_fact(monkeypatch):
    stub_model(
        monkeypatch,
        reconcile=lambda **_: _Result({"duplicates": [{"keep": 0, "drop": [30, "x", 0]}]}),
    )

    reconciled = reconcile([prepared("One."), prepared("Two.")])

    assert len(reconciled) == 2


def test_a_failed_reconcile_call_keeps_the_proposals(monkeypatch):
    """A duplicate that survives costs a reviewer a moment; a lost import costs
    them the document."""

    def explode(**_):
        raise RuntimeError("no")

    stub_model(monkeypatch, reconcile=explode)

    assert len(reconcile([prepared("One."), prepared("Two.")])) == 2


# --- the whole read ---


class _Result:
    """Stands in for mistral.JSONResult, which is all read_document touches."""

    def __init__(self, data):
        self.data = data


@pytest.fixture
def stub_reader(monkeypatch):
    """Every passage yields one proposal quoting its own first sentence."""

    def fake_extract(system, user, model=None):
        passage = user.split('PASSAGE\n"""\n', 1)[1].rsplit('\n"""', 1)[0]
        first = passage.split(".")[0].strip() + "."
        return _Result({"operations": [op(f"Neutral: {first}", quote=first)]})

    stub_model(
        monkeypatch,
        extract=fake_extract,
        reconcile=lambda **_: _Result({"duplicates": [], "revisions": []}),
    )


def test_reading_a_document_returns_proposals_with_provenance(stub_reader):
    result = read_document("spec.md", b"Sampling is 2 kHz.\n\nThe filter debounces.")

    assert result["document"] == "spec.md"
    assert result["passages"] >= 1
    provenance = result["operations"][0]["provenance"]
    assert provenance["document"] == "spec.md"
    assert provenance["locations"]
    assert provenance["quote"] == "Sampling is 2 kHz."


def test_a_paraphrased_quote_keeps_the_fact_and_drops_the_quote(monkeypatch):
    stub_model(
        monkeypatch,
        extract=lambda **_: _Result(
            {"operations": [op("Sampling is 2 kHz.", quote="made up")]}
        ),
        reconcile=lambda **_: _Result({}),
    )

    result = read_document("spec.md", b"Sampling is 2 kHz.")

    assert len(result["operations"]) == 1
    assert "quote" not in result["operations"][0]["provenance"]


def test_an_unusable_proposal_is_counted_not_swallowed(monkeypatch):
    """A fact the reader thinks they imported and didn't is the failure that
    matters here."""
    stub_model(
        monkeypatch,
        extract=lambda **_: _Result({"operations": [{"op": "create", "content": {}}]}),
    )

    result = read_document("spec.md", b"Sampling is 2 kHz.")

    assert result["operations"] == []
    assert result["dropped"] == 1


def test_one_failing_passage_doesnt_lose_the_others(monkeypatch):
    calls = {"n": 0}

    def flaky(system, user, model=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("rate limited")
        return _Result({"operations": [op("A fact.")]})

    stub_model(
        monkeypatch,
        extract=flaky,
        reconcile=lambda **_: _Result({"duplicates": [], "revisions": []}),
    )
    text = "\n\n".join(f"Paragraph {n} states a fact." for n in range(200))

    result = read_document("spec.md", text.encode())

    assert result["failed_passages"] == 1
    assert result["operations"]


# --- the endpoint ---


@pytest.fixture
def project(client, signed_up):
    signed_up("ada")
    created = client.post("/api/projects", json={"name": "MedGuard"}).get_json()
    return created["id"]


def upload(client, project_id, name="spec.md", body=b"Sampling is 2 kHz."):
    return client.post(
        f"/api/projects/{project_id}/document",
        data={"file": (io.BytesIO(body), name)},
        content_type="multipart/form-data",
    )


def test_upload_returns_proposals_and_stores_nothing(client, project, stub_reader):
    response = upload(client, project)

    assert response.status_code == 200
    assert response.get_json()["operations"]
    # A file is not a licence to write to the IR — it still passes both gates.
    assert store.entries_for_project(project) == []
    assert store.requests_for_project(project) == []


def test_upload_refuses_an_unsupported_type(client, project, stub_reader):
    response = upload(client, project, name="protocol.docx", body=b"PK\x03\x04")

    assert response.status_code == 400
    assert ".docx" in response.get_json()["error"]


def test_upload_requires_a_file(client, project, stub_reader):
    response = client.post(
        f"/api/projects/{project}/document", data={}, content_type="multipart/form-data"
    )

    assert response.status_code == 400


def test_non_member_cannot_upload(client, project, signed_up, stub_reader):
    client.post("/api/logout")
    signed_up("bob")

    assert upload(client, project).status_code == 403


def test_upload_requires_login(client):
    assert (
        client.post(
            "/api/projects/any/document",
            data={"file": (io.BytesIO(b"x"), "a.md")},
            content_type="multipart/form-data",
        ).status_code
        == 401
    )


# --- provenance survives into the review queue ---


@pytest.fixture(autouse=True)
def no_conflict_calls(monkeypatch):
    """Merging now looks for contradictions, which is another model call. These
    tests are about reading documents, not about that."""
    monkeypatch.setattr(conflict_detection, "find_conflicts", lambda *a, **k: [])


@pytest.fixture
def queued(client, project, signed_up):
    """Submits as a non-admin, so the request is still in the queue to inspect.
    An admin's own submission is merged on the spot and never queues."""

    def _queued(body):
        client.post("/api/logout")
        signed_up("bob")
        client.post(f"/api/projects/{project}/join")
        return client.post(f"/api/projects/{project}/requests", json=body).get_json()[
            "requests"
        ]

    return _queued


def test_a_submitted_document_fact_says_where_it_came_from(client, project, queued):
    """Checking one proposal at gate 2 shouldn't mean re-reading the document."""
    [request] = queued(
        {
            "text": "spec.md",
            "operations": [
                {
                    "op": "create",
                    "content": {"statement": "Sampling is 2 kHz."},
                    "provenance": {
                        "document": "spec.md",
                        "locations": ["page 3"],
                        "quote": "sampling shall be 2 kHz",
                    },
                }
            ],
        }
    )

    assert request["source_text"] == "spec.md — page 3: “sampling shall be 2 kHz”"
    # Provenance is where the fact came from, not part of the fact.
    assert "provenance" not in request["operation"]


def test_a_typed_message_still_carries_its_own_text(client, project, queued):
    [request] = queued(
        {
            "text": "Bumped sampling to 2kHz.",
            "operations": [{"op": "create", "content": {"statement": "Sampling is 2 kHz."}}],
        }
    )

    assert request["source_text"] == "Bumped sampling to 2kHz."
