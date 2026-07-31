"""Read and write paths. The model is stubbed — these test our logic, not its
judgement.
"""

from urllib.parse import quote

import pytest

from ai import reprojection
from data import store
from routes import pipeline

SOURCE = "Bumped sampling rate to 2kHz."


def content(**overrides) -> dict:
    base = {"statement": "The sampling rate was raised to 2 kHz."}
    base.update(overrides)
    return base


@pytest.fixture
def project(client, signed_up):
    """An admin with a project, logged in."""
    owner = signed_up("ada")
    created = client.post("/api/projects", json={"name": "MedGuard"}).get_json()
    return {"owner": owner, "id": created["id"]}


@pytest.fixture
def stub_model(monkeypatch):
    """Replaces every model call with something deterministic."""
    calls = {"read": 0, "summarize": 0, "welcome": 0, "answer": 0, "conflicts": 0}

    def fake_read(text, profile=None, existing=None, model=None):
        calls["read"] += 1
        asked = text.strip().endswith("?")
        return {
            # A question-only message proposes nothing; anything else proposes
            # one change. Both together when it does both.
            "operations": [] if asked else [{"op": "create", "content": content()}],
            "answer": "An answer." if asked else None,
            "dropped": 0,
        }

    def fake_summarize(entries, profile, model=None):
        calls["summarize"] += 1
        ids = [entry["id"] for entry in entries]
        return {
            "segments": [{"text": "A summary.", "source_entry_ids": ids[:1]}],
        }

    def fake_answer(question, entries, profile, model=None):
        calls["answer"] += 1
        ids = [entry["id"] for entry in entries]
        return {"segments": [{"text": "An answer.", "source_entry_ids": ids[:1]}]}

    def fake_welcome(profile, model=None):
        calls["welcome"] += 1
        return {"text": "A welcome."}

    def fake_conflicts(landed, existing, model=None):
        calls["conflicts"] += 1
        return []

    monkeypatch.setattr(pipeline, "interpret_message", fake_read)
    monkeypatch.setattr(pipeline.reprojection, "summarize", fake_summarize)
    monkeypatch.setattr(pipeline.reprojection, "answer", fake_answer)
    monkeypatch.setattr(pipeline.reprojection, "welcome", fake_welcome)
    monkeypatch.setattr(
        pipeline.conflict_detection, "find_conflicts", fake_conflicts
    )
    reprojection._cache.clear()
    reprojection._welcome_cache.clear()
    return calls


def submit(client, project_id, operations=None):
    """Submits changes, returning {"requests": [...], "merged": [...]}."""
    return client.post(
        f"/api/projects/{project_id}/requests",
        json={
            "text": SOURCE,
            "operations": operations or [{"op": "create", "content": content()}],
        },
    ).get_json()


def merge_a_change(client, project_id, operations=None):
    """Gets changes into the IR, returning the affected entry ids.

    The caller here is the admin who owns the project, so submitting merges
    on the spot — there is nothing left to approve.
    """
    return submit(client, project_id, operations)["merged"]


@pytest.fixture
def queued(client, project, signed_up):
    """Submits as a non-admin, so the request is still pending, then puts the
    admin back in the session to act on it. Returns the pending requests."""

    def _queued(operations=None):
        client.post("/api/logout")
        member = signed_up("bob")
        client.post(f"/api/projects/{project['id']}/join")
        pending = submit(client, project["id"], operations)["requests"]

        client.post("/api/logout")
        client.post("/api/login", json={"username": "ada", "password": "pw"})
        return pending, member

    return _queued


# --- input: one box, two paths ---


def test_statement_proposes_changes_and_stores_nothing(client, project, stub_model):
    response = client.post(f"/api/projects/{project['id']}/input", json={"text": SOURCE})

    assert response.status_code == 200
    body = response.get_json()
    assert len(body["operations"]) == 1
    assert body["answer"] is None
    # Nothing lands until the author accepts.
    assert store.entries_for_project(project["id"]) == []
    assert store.requests_for_project(project["id"]) == []


def test_question_returns_an_answer(client, project, stub_model):
    merge_a_change(client, project["id"])

    response = client.post(
        f"/api/projects/{project['id']}/input", json={"text": "what changed?"}
    )

    body = response.get_json()
    assert body["answer"] == "An answer."
    # A question proposes nothing.
    assert body["operations"] == []


def test_answers_carry_the_entries_they_drew_on(client, project, stub_model):
    """An answer is traceable for the same reason the summary is."""
    entry_ids = merge_a_change(client, project["id"])

    body = client.post(
        f"/api/projects/{project['id']}/input", json={"text": "what changed?"}
    ).get_json()

    assert body["answer_segments"][0]["source_entry_ids"] == entry_ids[:1]
    assert stub_model["answer"] == 1


def test_an_answer_may_reason_beyond_the_record(client, project, stub_model):
    """"Who is this for?" has no recorded answer, and inferring one is the
    useful reply. Uncited segments survive in an answer — carrying no marker,
    which is what tells the reader it's inference — but never in a summary."""
    segments = [
        {"text": "The record says 2 kHz.", "source_entry_ids": ["real"]},
        {"text": "So this is probably for outpatients.", "source_entry_ids": []},
    ]

    answer = reprojection.keep_grounded_segments(
        segments, {"real"}, require_citation=False
    )
    summary = reprojection.keep_grounded_segments(segments, {"real"})

    assert [segment["text"] for segment in answer] == [
        "The record says 2 kHz.",
        "So this is probably for outpatients.",
    ]
    assert [segment["text"] for segment in summary] == ["The record says 2 kHz."]


def test_a_statement_needs_no_answer_call(client, project, stub_model):
    client.post(f"/api/projects/{project['id']}/input", json={"text": SOURCE})

    assert stub_model["answer"] == 0


def test_one_call_covers_both_paths(client, project, stub_model):
    # No classifier to disagree with: a message that states and asks does both.
    client.post(f"/api/projects/{project['id']}/input", json={"text": SOURCE})
    client.post(f"/api/projects/{project['id']}/input", json={"text": "what changed?"})

    assert stub_model["read"] == 2


def test_input_requires_text(client, project, stub_model):
    assert (
        client.post(f"/api/projects/{project['id']}/input", json={"text": "  "}).status_code
        == 400
    )


def test_non_member_cannot_use_input(client, project, signed_up, stub_model):
    client.post("/api/logout")
    signed_up("bob")
    assert (
        client.post(f"/api/projects/{project['id']}/input", json={"text": SOURCE}).status_code
        == 403
    )


# --- write path ---


def test_an_admins_own_submission_lands_immediately(client, project, stub_model):
    """Confirming at gate 1 is the only decision gate 2 would have asked for,
    so an admin isn't made to approve what they just approved."""
    response = client.post(
        f"/api/projects/{project['id']}/requests",
        json={"text": SOURCE, "operations": [{"op": "create", "content": content()}]},
    )

    assert response.status_code == 201
    body = response.get_json()
    assert body["requests"] == []
    assert len(body["merged"]) == 1
    assert len(store.entries_for_project(project["id"])) == 1
    assert store.requests_for_project(project["id"]) == []


def test_a_members_submission_still_waits(client, project, queued, stub_model):
    """The gate is only skipped for someone who could open it anyway."""
    pending, _ = queued()

    assert len(pending) == 1
    assert len(store.requests_for_project(project["id"])) == 1
    assert store.entries_for_project(project["id"]) == []


def test_each_proposed_change_becomes_its_own_request(client, project, queued, stub_model):
    # So an admin can merge one and reject another, rather than being handed
    # a bundle to take or leave.
    created, _ = queued(
        [
            {"op": "create", "content": content(statement="First.")},
            {"op": "create", "content": content(statement="Second.")},
        ]
    )

    assert len(created) == 2
    pending = store.requests_for_project(project["id"])
    assert len(pending) == 2
    assert {p["operation"]["content"]["statement"] for p in pending} == {"First.", "Second."}


def test_one_request_can_be_merged_while_another_is_rejected(client, project, queued, stub_model):
    (first, second), _ = queued(
        [
            {"op": "create", "content": content(statement="Keep this.")},
            {"op": "create", "content": content(statement="Drop this.")},
        ]
    )

    client.post(f"/api/projects/{project['id']}/requests/{first['id']}/merge")
    client.post(f"/api/projects/{project['id']}/requests/{second['id']}/reject")

    entries = store.entries_for_project(project["id"])
    assert [entry["content"]["statement"] for entry in entries] == ["Keep this."]
    assert store.requests_for_project(project["id"]) == []


def test_merging_applies_the_change_and_clears_the_request(client, project, queued, stub_model):
    [pending], _ = queued()
    applied = [
        client.post(
            f"/api/projects/{project['id']}/requests/{pending['id']}/merge"
        ).get_json()["merged"]
    ]

    entries = store.entries_for_project(project["id"])
    assert [entry["id"] for entry in entries] == applied
    assert entries[0]["content"]["statement"] == content()["statement"]
    assert store.requests_for_project(project["id"]) == []


def test_applied_entry_is_authored_by_the_proposer(client, project, queued, stub_model):
    # Bob submits; Ada (admin) merges. The fact is Bob's.
    [request], bob = queued()
    client.post(f"/api/projects/{project['id']}/requests/{request['id']}/merge")

    assert store.entries_for_project(project["id"])[0]["author"] == bob["id"]


def test_non_admin_cannot_merge(client, project, signed_up, stub_model):
    client.post("/api/logout")
    signed_up("bob")
    client.post(f"/api/projects/{project['id']}/join")
    [request] = submit(client, project["id"])["requests"]

    response = client.post(
        f"/api/projects/{project['id']}/requests/{request['id']}/merge"
    )

    assert response.status_code == 403
    assert store.entries_for_project(project["id"]) == []


def test_update_operation_revises_in_place(client, project, stub_model):
    [entry_id] = merge_a_change(client, project["id"])

    applied = merge_a_change(
        client,
        project["id"],
        [{"op": "update", "target_id": entry_id, "content": content(statement="Now 4 kHz.")}],
    )

    entries = store.entries_for_project(project["id"])
    assert applied == [entry_id]
    # Revised, not duplicated.
    assert len(entries) == 1
    assert entries[0]["content"]["statement"] == "Now 4 kHz."


def test_update_targeting_a_vanished_entry_is_refused(client, project, stub_model):
    # It can't be created at accept time, so plant it straight into the store.
    pending = store.create_request(
        project["id"],
        author=project["owner"]["id"],
        source_text=SOURCE,
        operation={"op": "update", "target_id": "ghost", "content": content()},
    )

    response = client.post(
        f"/api/projects/{project['id']}/requests/{pending['id']}/merge"
    )

    assert response.status_code == 409
    # Refused rather than quietly landing as a create.
    assert store.entries_for_project(project["id"]) == []
    assert len(store.requests_for_project(project["id"])) == 1


def test_rejecting_deletes_the_request(client, project, queued, stub_model):
    [request], _ = queued()

    assert (
        client.post(
            f"/api/projects/{project['id']}/requests/{request['id']}/reject"
        ).status_code
        == 204
    )
    assert store.requests_for_project(project["id"]) == []
    assert store.entries_for_project(project["id"]) == []


def test_author_can_edit_their_pending_request(client, project, queued, stub_model):
    [request], _ = queued()

    response = client.put(
        f"/api/projects/{project['id']}/requests/{request['id']}",
        json={"operation": {"op": "create", "content": content(statement="Corrected.")}},
    )

    assert response.status_code == 200
    assert response.get_json()["operation"]["content"]["statement"] == "Corrected."


def test_hand_edits_are_validated_too(client, project, queued, stub_model):
    # The editable path skips the model, so it must not skip the model's checks.
    [request], _ = queued()

    # An update aimed at an entry that doesn't exist would land as a create.
    assert (
        client.put(
            f"/api/projects/{project['id']}/requests/{request['id']}",
            json={"operation": {"op": "update", "target_id": "ghost", "content": content()}},
        ).status_code
        == 400
    )

    # A statement is the one thing every entry needs to be displayable.
    assert (
        client.put(
            f"/api/projects/{project['id']}/requests/{request['id']}",
            json={"operation": {"op": "create", "content": {"note": "no statement"}}},
        ).status_code
        == 400
    )


def test_stranger_cannot_edit_someone_elses_request(client, project, queued, signed_up, stub_model):
    # Bob proposes; Carol is a member but neither its author nor an admin.
    [request], _ = queued()

    client.post("/api/logout")
    signed_up("carol")
    client.post(f"/api/projects/{project['id']}/join")

    response = client.put(
        f"/api/projects/{project['id']}/requests/{request['id']}",
        json={"operation": {"op": "create", "content": content()}},
    )
    assert response.status_code == 403


# --- view, changes, caching ---


def test_view_returns_grounded_segments(client, project, stub_model):
    merge_a_change(client, project["id"])

    body = client.get(f"/api/projects/{project['id']}/view").get_json()

    assert body["segments"][0]["text"] == "A summary."
    assert body["cached"] is False


def test_empty_project_is_welcomed_rather_than_summarized(client, project, stub_model):
    """Nothing to summarize, but the reader is still someone in particular."""
    body = client.get(f"/api/projects/{project['id']}/view").get_json()

    assert body["segments"] == []
    assert body["welcome"] == "A welcome."
    assert stub_model["summarize"] == 0
    assert stub_model["welcome"] == 1


def test_entry_ids_are_stripped_from_summary_prose(client, project, stub_model):
    """Ids belong in source_entry_ids. The model inlines them into the text
    anyway, so they're removed in code rather than asked for in the prompt."""
    entry_id = "24f65462-b121-4afd-93ba-2f46ae51410d"
    segments = [
        {
            "text": f"The rate ({entry_id}) is fixed, per the filter "
            f"({entry_id}, {entry_id}).",
            "source_entry_ids": [entry_id],
        }
    ]

    grounded = reprojection.keep_grounded_segments(segments, {entry_id})

    assert grounded[0]["text"] == "The rate is fixed, per the filter."
    assert grounded[0]["source_entry_ids"] == [entry_id]


def test_second_view_is_served_from_cache(client, project, stub_model):
    merge_a_change(client, project["id"])

    client.get(f"/api/projects/{project['id']}/view")
    second = client.get(f"/api/projects/{project['id']}/view").get_json()

    assert second["cached"] is True
    assert stub_model["summarize"] == 1


def test_a_new_entry_busts_the_cache(client, project, stub_model):
    merge_a_change(client, project["id"])
    client.get(f"/api/projects/{project['id']}/view")

    merge_a_change(client, project["id"])
    body = client.get(f"/api/projects/{project['id']}/view").get_json()

    assert body["cached"] is False
    assert stub_model["summarize"] == 2


def test_editing_your_profile_busts_the_cache(client, project, stub_model):
    merge_a_change(client, project["id"])
    client.get(f"/api/projects/{project['id']}/view")

    client.put("/api/profiles/me", json={"content": {"description": "now a lawyer"}})
    body = client.get(f"/api/projects/{project['id']}/view").get_json()

    # The summary depends on who's reading, so a changed self-description has to
    # invalidate it as surely as a changed fact.
    assert body["cached"] is False
    assert stub_model["summarize"] == 2


def test_changes_since_filters_by_timestamp(client, project, stub_model):
    merge_a_change(client, project["id"])
    entries = store.entries_for_project(project["id"])

    everything = client.get(f"/api/projects/{project['id']}/changes").get_json()
    assert len(everything) == 1

    # Unencoded on purpose: a "+00:00" offset arrives as " 00:00", which used to
    # make the filter silently return everything.
    nothing = client.get(
        f"/api/projects/{project['id']}/changes?since={entries[0]['created_at']}"
    ).get_json()
    assert nothing == []

    encoded = quote(entries[0]["created_at"])
    assert client.get(f"/api/projects/{project['id']}/changes?since={encoded}").get_json() == []


def test_pipeline_endpoints_require_login(client):
    assert client.post("/api/projects/any/input", json={"text": "x"}).status_code == 401
    assert client.get("/api/projects/any/view").status_code == 401
    assert client.get("/api/projects/any/changes").status_code == 401
    assert client.get("/api/projects/any/requests").status_code == 401
    assert client.post("/api/projects/any/requests/r/merge").status_code == 401
