"""Two facts in the record that can't both be true.

The detector is stubbed — what's under test is that a contradiction is found
where the IR changes, that only an admin can settle one, and that settling it
actually settles it.
"""

import pytest

from ai import conflicts as conflict_detection
from data import store
from routes import pipeline

CONTENT = {"statement": "The front-end samples at 2 kHz."}
OTHER = {"statement": "The study was run against 1 kHz sampling."}


@pytest.fixture
def project(client, signed_up):
    """An admin with a project, logged in."""
    owner = signed_up("ada")
    created = client.post("/api/projects", json={"name": "MedGuard"}).get_json()
    return {"owner": owner, "id": created["id"]}


@pytest.fixture
def detector(monkeypatch):
    """Reports a conflict between entries whose statements the test has named.

    Keyed on statements rather than on whatever it was handed, so the same two
    facts are flagged every time they're compared — which is the whole point of
    testing that a pair is recorded once and a dismissal sticks.
    """
    contradicts: set[str] = set()

    def fake(landed, existing, model=None):
        ids = [
            entry["id"]
            for entry in landed + existing
            if entry["content"].get("statement") in contradicts
        ]
        if len(ids) < 2:
            return []
        return [{"a": ids[0], "b": ids[1], "reason": "Sampling rate."}]

    monkeypatch.setattr(conflict_detection, "find_conflicts", fake)
    monkeypatch.setattr(pipeline.conflict_detection, "find_conflicts", fake)
    return contradicts


def add(client, project_id, content):
    """Admin submits, which merges on the spot, returning the entry id."""
    [entry_id] = client.post(
        f"/api/projects/{project_id}/requests",
        json={"text": "note", "operations": [{"op": "create", "content": content}]},
    ).get_json()["merged"]
    return entry_id


def conflicts(client, project_id):
    return client.get(f"/api/projects/{project_id}/conflicts").get_json()


# --- detection ---


def test_a_contradiction_is_found_where_the_ir_changes(client, project, detector):
    add(client, project["id"], CONTENT)
    detector.update({CONTENT["statement"], OTHER["statement"]})
    add(client, project["id"], OTHER)

    [conflict] = conflicts(client, project["id"])
    assert len(conflict["entry_ids"]) == 2
    assert conflict["reason"] == "Sampling rate."


def test_the_first_fact_conflicts_with_nothing(client, project, detector):
    detector.update({CONTENT["statement"], OTHER["statement"]})
    add(client, project["id"], CONTENT)

    # Nothing to contradict yet, so the detector isn't even asked.
    assert conflicts(client, project["id"]) == []


def test_the_same_pair_is_only_recorded_once(client, project, detector):
    add(client, project["id"], CONTENT)
    detector.update({CONTENT["statement"], OTHER["statement"]})
    add(client, project["id"], OTHER)
    add(client, project["id"], {"statement": "A third, unrelated fact."})

    assert len(conflicts(client, project["id"])) == 1


# --- who can settle one ---


def test_everyone_can_see_conflicts(client, project, detector, signed_up):
    """The record contradicting itself is everyone's problem to know about."""
    add(client, project["id"], CONTENT)
    detector.update({CONTENT["statement"], OTHER["statement"]})
    add(client, project["id"], OTHER)

    client.post("/api/logout")
    signed_up("bob")
    client.post(f"/api/projects/{project['id']}/join")

    assert len(conflicts(client, project["id"])) == 1


def test_a_non_admin_cannot_resolve(client, project, detector, signed_up):
    add(client, project["id"], CONTENT)
    detector.update({CONTENT["statement"], OTHER["statement"]})
    add(client, project["id"], OTHER)
    [conflict] = conflicts(client, project["id"])
    entry_id = conflict["entry_ids"][0]

    client.post("/api/logout")
    signed_up("bob")
    client.post(f"/api/projects/{project['id']}/join")

    assert (
        client.post(
            f"/api/projects/{project['id']}/conflicts/{conflict['id']}"
            f"/discard/{entry_id}"
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/projects/{project['id']}/conflicts/{conflict['id']}/dismiss"
        ).status_code
        == 403
    )
    assert len(store.entries_for_project(project["id"])) == 2


# --- settling one ---


def test_an_edit_that_resolves_it_clears_it(client, project, detector):
    add(client, project["id"], CONTENT)
    detector.update({CONTENT["statement"], OTHER["statement"]})
    add(client, project["id"], OTHER)
    [conflict] = conflicts(client, project["id"])
    entry_id = conflict["entry_ids"][0]

    response = client.put(
        f"/api/projects/{project['id']}/conflicts/{conflict['id']}/entries/{entry_id}",
        json={"content": {"statement": "The front-end samples at 1 kHz."}},
    )

    assert response.get_json() == {"resolved": True}
    assert conflicts(client, project["id"]) == []
    entries = {entry["id"]: entry for entry in store.entries_for_project(project["id"])}
    assert entries[entry_id]["content"]["statement"] == "The front-end samples at 1 kHz."


def test_an_edit_that_doesnt_resolve_it_keeps_it(client, project, detector):
    """Otherwise "resolving" a conflict is just closing the dialog."""
    add(client, project["id"], CONTENT)
    detector.update({CONTENT["statement"], OTHER["statement"]})
    add(client, project["id"], OTHER)
    [conflict] = conflicts(client, project["id"])

    detector.add("The front-end samples at 4 kHz.")
    response = client.put(
        f"/api/projects/{project['id']}/conflicts/{conflict['id']}"
        f"/entries/{conflict['entry_ids'][0]}",
        json={"content": {"statement": "The front-end samples at 4 kHz."}},
    )

    assert response.get_json() == {"resolved": False}
    assert len(conflicts(client, project["id"])) == 1


def test_an_edit_still_needs_a_statement(client, project, detector):
    add(client, project["id"], CONTENT)
    detector.update({CONTENT["statement"], OTHER["statement"]})
    add(client, project["id"], OTHER)
    [conflict] = conflicts(client, project["id"])

    assert (
        client.put(
            f"/api/projects/{project['id']}/conflicts/{conflict['id']}"
            f"/entries/{conflict['entry_ids'][0]}",
            json={"content": {"note": "no statement"}},
        ).status_code
        == 400
    )


def test_editing_an_entry_outside_the_conflict_is_refused(client, project, detector):
    add(client, project["id"], CONTENT)
    detector.update({CONTENT["statement"], OTHER["statement"]})
    add(client, project["id"], OTHER)
    outsider = add(client, project["id"], {"statement": "Unrelated."})
    [conflict] = conflicts(client, project["id"])

    assert (
        client.put(
            f"/api/projects/{project['id']}/conflicts/{conflict['id']}"
            f"/entries/{outsider}",
            json={"content": {"statement": "Changed."}},
        ).status_code
        == 400
    )


def test_discarding_drops_the_fact_and_the_conflict(client, project, detector):
    add(client, project["id"], CONTENT)
    detector.update({CONTENT["statement"], OTHER["statement"]})
    add(client, project["id"], OTHER)
    [conflict] = conflicts(client, project["id"])
    discarded = conflict["entry_ids"][0]

    client.post(
        f"/api/projects/{project['id']}/conflicts/{conflict['id']}/discard/{discarded}"
    )

    remaining = [entry["id"] for entry in store.entries_for_project(project["id"])]
    assert discarded not in remaining
    assert len(remaining) == 1
    assert conflicts(client, project["id"]) == []


def test_a_dismissal_survives_the_next_merge(client, project, detector):
    """"These don't actually contradict" is a ruling. Re-raising the same pair
    on the next merge would make it meaningless."""
    add(client, project["id"], CONTENT)
    detector.update({CONTENT["statement"], OTHER["statement"]})
    add(client, project["id"], OTHER)
    [conflict] = conflicts(client, project["id"])

    client.post(f"/api/projects/{project['id']}/conflicts/{conflict['id']}/dismiss")
    assert conflicts(client, project["id"]) == []

    # The detector still reports the same pair; it must not come back.
    add(client, project["id"], {"statement": "Something else entirely."})
    assert conflicts(client, project["id"]) == []


# --- the detector's own checks ---


def test_a_pair_naming_an_unknown_entry_is_dropped(monkeypatch):
    """The model will name an id that isn't there. Checked in code, like
    citations — a pair we can't resolve is a hallucination, not a conflict."""

    class _Result:
        data = {
            "conflicts": [
                {"a": "e-1", "b": "ghost", "reason": "no"},
                {"a": "e-1", "b": "e-1", "reason": "itself"},
                {"a": "e-1", "b": "e-2", "reason": "Sampling rate."},
            ]
        }

    monkeypatch.setattr(
        conflict_detection.mistral, "complete_json", lambda **_: _Result()
    )

    found = conflict_detection.find_conflicts(
        [{"id": "e-1", "content": CONTENT}], [{"id": "e-2", "content": OTHER}]
    )

    assert found == [{"a": "e-1", "b": "e-2", "reason": "Sampling rate."}]


def test_a_failed_detector_call_doesnt_fail_the_merge(monkeypatch):
    def explode(**_):
        raise RuntimeError("rate limited")

    monkeypatch.setattr(conflict_detection.mistral, "complete_json", explode)

    assert (
        conflict_detection.find_conflicts(
            [{"id": "e-1", "content": CONTENT}], [{"id": "e-2", "content": OTHER}]
        )
        == []
    )
