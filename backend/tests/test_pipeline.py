"""Read and write paths. The model is stubbed — these test our logic, not its
judgement; `eval_extraction.py` is where prompt quality gets judged.
"""

from urllib.parse import quote

import pytest

import pipeline
import reprojection
import store

SOURCE = "Bumped sampling rate to 2kHz."


def content(**overrides) -> dict:
    base = {
        "statement": "The sampling rate was raised to 2 kHz.",
        "subject": "sampling rate",
        "source_quote": "Bumped sampling rate to 2kHz",
        "certainty": "stated",
    }
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
    calls = {"classify": 0, "extract": 0, "answer": 0, "summarize": 0}

    def fake_classify(text, model=None):
        calls["classify"] += 1
        return "question" if text.strip().endswith("?") else "statement"

    def fake_extract(text, profile=None, existing=None, model=None):
        calls["extract"] += 1
        return {
            "operations": [{"op": "create", "content": content()}],
            "unresolved": [],
            "rejected": [],
            "diagnostics": {},
        }

    def fake_answer(question, entries, profile, model=None):
        calls["answer"] += 1
        ids = [entry["id"] for entry in entries]
        return {
            "segments": [{"text": "An answer.", "source_entry_ids": ids[:1]}] if ids else [],
            "diagnostics": {},
        }

    def fake_summarize(entries, profile, model=None):
        calls["summarize"] += 1
        ids = [entry["id"] for entry in entries]
        return {
            "segments": [{"text": "A summary.", "source_entry_ids": ids[:1]}],
            "diagnostics": {},
        }

    monkeypatch.setattr(pipeline, "classify", fake_classify)
    monkeypatch.setattr(pipeline, "extract_changeset", fake_extract)
    monkeypatch.setattr(reprojection, "answer", fake_answer)
    monkeypatch.setattr(pipeline.reprojection, "summarize", fake_summarize)
    reprojection._cache.clear()
    return calls


def approve_a_change(client, project_id, operations=None):
    """Runs a changeset through confirm + approve, returning the new entry ids."""
    request = client.post(
        f"/api/projects/{project_id}/requests",
        json={
            "text": SOURCE,
            "operations": operations or [{"op": "create", "content": content()}],
        },
    ).get_json()
    return client.post(
        f"/api/projects/{project_id}/requests/{request['id']}/approve"
    ).get_json()["applied"]


# --- input: one box, two paths ---


def test_statement_returns_a_changeset_and_stores_nothing(client, project, stub_model):
    response = client.post(f"/api/projects/{project['id']}/input", json={"text": SOURCE})

    assert response.status_code == 200
    assert response.get_json()["kind"] == "changeset"
    # Nothing lands until the author confirms.
    assert store.entries_for_project(project["id"]) == []
    assert store.requests_for_project(project["id"]) == []


def test_question_returns_an_answer(client, project, stub_model):
    approve_a_change(client, project["id"])

    response = client.post(
        f"/api/projects/{project['id']}/input", json={"text": "what changed?"}
    )

    body = response.get_json()
    assert body["kind"] == "answer"
    assert body["segments"][0]["text"] == "An answer."


def test_kind_override_beats_the_classifier(client, project, stub_model):
    # "treat it as the other thing" — a question forced down the statement path.
    response = client.post(
        f"/api/projects/{project['id']}/input",
        json={"text": "what changed?", "kind": "changeset"},
    )

    assert response.get_json()["kind"] == "changeset"
    assert stub_model["classify"] == 0


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


def test_confirming_creates_a_pending_request_even_for_an_admin(client, project, stub_model):
    response = client.post(
        f"/api/projects/{project['id']}/requests",
        json={"text": SOURCE, "operations": [{"op": "create", "content": content()}]},
    )

    assert response.status_code == 201
    # One path for everyone: being an admin doesn't skip the queue.
    assert len(store.requests_for_project(project["id"])) == 1
    assert store.entries_for_project(project["id"]) == []


def test_approving_applies_the_changeset_and_clears_the_request(client, project, stub_model):
    applied = approve_a_change(client, project["id"])

    entries = store.entries_for_project(project["id"])
    assert [entry["id"] for entry in entries] == applied
    assert entries[0]["content"]["subject"] == "sampling rate"
    assert store.requests_for_project(project["id"]) == []


def test_applied_entry_is_authored_by_the_proposer(client, project, signed_up, stub_model):
    # Bob proposes; Ada (admin) approves. The fact is Bob's.
    client.post("/api/logout")
    bob = signed_up("bob")
    client.post(f"/api/projects/{project['id']}/join")
    request = client.post(
        f"/api/projects/{project['id']}/requests",
        json={"text": SOURCE, "operations": [{"op": "create", "content": content()}]},
    ).get_json()

    client.post("/api/logout")
    client.post("/api/login", json={"username": "ada", "password": "pw"})
    client.post(f"/api/projects/{project['id']}/requests/{request['id']}/approve")

    assert store.entries_for_project(project["id"])[0]["author"] == bob["id"]


def test_non_admin_cannot_approve(client, project, signed_up, stub_model):
    client.post("/api/logout")
    signed_up("bob")
    client.post(f"/api/projects/{project['id']}/join")
    request = client.post(
        f"/api/projects/{project['id']}/requests",
        json={"text": SOURCE, "operations": [{"op": "create", "content": content()}]},
    ).get_json()

    response = client.post(
        f"/api/projects/{project['id']}/requests/{request['id']}/approve"
    )

    assert response.status_code == 403
    assert store.entries_for_project(project["id"]) == []


def test_update_operation_revises_in_place(client, project, stub_model):
    [entry_id] = approve_a_change(client, project["id"])

    applied = approve_a_change(
        client,
        project["id"],
        [{"op": "update", "target_id": entry_id, "content": content(statement="Now 4 kHz.")}],
    )

    entries = store.entries_for_project(project["id"])
    assert applied == [entry_id]
    # Revised, not duplicated.
    assert len(entries) == 1
    assert entries[0]["content"]["statement"] == "Now 4 kHz."


def test_update_targeting_a_vanished_entry_applies_nothing(client, project, stub_model):
    request = client.post(
        f"/api/projects/{project['id']}/requests",
        json={
            "text": SOURCE,
            "operations": [
                {"op": "create", "content": content()},
                {"op": "update", "target_id": "ghost", "content": content()},
            ],
        },
    ).get_json()

    response = client.post(
        f"/api/projects/{project['id']}/requests/{request['id']}/approve"
    )

    assert response.status_code == 409
    # All or nothing: the create alongside it must not have landed either.
    assert store.entries_for_project(project["id"]) == []
    assert len(store.requests_for_project(project["id"])) == 1


def test_rejecting_deletes_the_request(client, project, stub_model):
    request = client.post(
        f"/api/projects/{project['id']}/requests",
        json={"text": SOURCE, "operations": [{"op": "create", "content": content()}]},
    ).get_json()

    assert (
        client.post(
            f"/api/projects/{project['id']}/requests/{request['id']}/reject"
        ).status_code
        == 204
    )
    assert store.requests_for_project(project["id"]) == []
    assert store.entries_for_project(project["id"]) == []


def test_author_can_edit_their_pending_request(client, project, stub_model):
    request = client.post(
        f"/api/projects/{project['id']}/requests",
        json={"text": SOURCE, "operations": [{"op": "create", "content": content()}]},
    ).get_json()

    response = client.put(
        f"/api/projects/{project['id']}/requests/{request['id']}",
        json={"operations": [{"op": "create", "content": content(statement="Corrected.")}]},
    )

    assert response.status_code == 200
    assert response.get_json()["operations"][0]["content"]["statement"] == "Corrected."


def test_hand_edits_are_validated_too(client, project, stub_model):
    # The editable path must not become a hole in the grounding guardrail.
    request = client.post(
        f"/api/projects/{project['id']}/requests",
        json={"text": SOURCE, "operations": [{"op": "create", "content": content()}]},
    ).get_json()

    response = client.put(
        f"/api/projects/{project['id']}/requests/{request['id']}",
        json={
            "operations": [
                {"op": "create", "content": content(source_quote="never said this")}
            ]
        },
    )

    assert response.status_code == 400
    assert any("not verbatim" in problem for problem in response.get_json()["problems"])


def test_stranger_cannot_edit_someone_elses_request(client, project, signed_up, stub_model):
    request = client.post(
        f"/api/projects/{project['id']}/requests",
        json={"text": SOURCE, "operations": [{"op": "create", "content": content()}]},
    ).get_json()

    client.post("/api/logout")
    signed_up("bob")
    client.post(f"/api/projects/{project['id']}/join")

    response = client.put(
        f"/api/projects/{project['id']}/requests/{request['id']}",
        json={"operations": [{"op": "create", "content": content()}]},
    )
    assert response.status_code == 403


# --- view, changes, caching ---


def test_view_returns_grounded_segments(client, project, stub_model):
    approve_a_change(client, project["id"])

    body = client.get(f"/api/projects/{project['id']}/view").get_json()

    assert body["segments"][0]["text"] == "A summary."
    assert body["cached"] is False


def test_empty_project_needs_no_model_call(client, project, stub_model):
    body = client.get(f"/api/projects/{project['id']}/view").get_json()

    assert body["segments"] == []
    assert stub_model["summarize"] == 0


def test_second_view_is_served_from_cache(client, project, stub_model):
    approve_a_change(client, project["id"])

    client.get(f"/api/projects/{project['id']}/view")
    second = client.get(f"/api/projects/{project['id']}/view").get_json()

    assert second["cached"] is True
    assert stub_model["summarize"] == 1


def test_a_new_entry_busts_the_cache(client, project, stub_model):
    approve_a_change(client, project["id"])
    client.get(f"/api/projects/{project['id']}/view")

    approve_a_change(client, project["id"])
    body = client.get(f"/api/projects/{project['id']}/view").get_json()

    assert body["cached"] is False
    assert stub_model["summarize"] == 2


def test_editing_your_profile_busts_the_cache(client, project, stub_model):
    approve_a_change(client, project["id"])
    client.get(f"/api/projects/{project['id']}/view")

    client.put("/api/profiles/me", json={"content": {"description": "now a lawyer"}})
    body = client.get(f"/api/projects/{project['id']}/view").get_json()

    # The summary depends on who's reading, so a changed self-description has to
    # invalidate it as surely as a changed fact.
    assert body["cached"] is False
    assert stub_model["summarize"] == 2


def test_changes_since_filters_by_timestamp(client, project, stub_model):
    approve_a_change(client, project["id"])
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
    assert client.post("/api/projects/any/requests/r/approve").status_code == 401
