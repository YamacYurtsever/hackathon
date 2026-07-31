from io import BytesIO
from pathlib import Path

import pytest

from app import create_app
from mistral_service import MistralProcessingError
from storage import JsonStore


class FakeMistralService:
    configured = True

    def __init__(self) -> None:
        self.last_entries = []
        self.conflict_to_detect = False
        self.conflict_error = False
        self.conflict_review_calls = []

    def process_document(self, content: bytes, mime_type: str):
        assert content
        assert mime_type == "application/pdf"
        return {
            "pages": [
                {
                    "page": 1,
                    "markdown": "The sampling rate is 2 kHz.",
                }
            ],
            "facts": [
                {
                    "statement": "The sampling rate is 2 kHz.",
                    "category": "metric",
                    "entities": ["sampling rate"],
                    "source": {
                        "page": 1,
                        "quote": "The sampling rate is 2 kHz.",
                    },
                    "confidence": "high",
                }
            ],
            "ocr_model": "fake-ocr",
            "chat_model": "fake-chat",
        }

    def answer_question(self, question, entries, history):
        self.last_entries = entries
        assert question == "What is the sampling rate?"
        assert history == []
        entry = entries[0]
        return {
            "answer": "The sampling rate is 2 kHz.",
            "insufficient_evidence": False,
            "citations": [
                {
                    "entry_id": entry["id"],
                    "statement": entry["content"]["statement"],
                    "page": 1,
                    "quote": entry["content"]["source"]["quote"],
                }
            ],
            "model": "fake-chat",
        }

    def extract_message(self, message, author_profile):
        assert author_profile["name"] == "Maya"
        return [
            {
                "statement": "The debounce filter was enabled.",
                "category": "change",
                "entities": ["debounce filter"],
                "source": {
                    "kind": "message",
                    "page": None,
                    "quote": message,
                },
                "confidence": "high",
            }
        ]

    def reproject_entries(self, entries, viewer_profile):
        assert viewer_profile["name"] == "Maya"
        return [
            {
                "id": f"claim_{entries[0]['id']}_1",
                "text": "The filter change affects your firmware baseline.",
                "entry_id": entries[0]["id"],
                "grounding": [
                    {
                        "entry_id": entries[0]["id"],
                        "path": "content.statement",
                        "value": entries[0]["content"]["statement"],
                    }
                ],
                "is_implication": True,
            }
        ]

    def detect_conflicts(
        self,
        new_entries,
        existing_entries,
        members,
        open_issues,
    ):
        self.conflict_review_calls.append(
            {
                "new_entries": new_entries,
                "existing_entries": existing_entries,
                "members": members,
                "open_issues": open_issues,
            }
        )
        if self.conflict_error:
            raise MistralProcessingError("Conflict review unavailable.")
        if not self.conflict_to_detect:
            return []
        participant_id = new_entries[0]["author"]
        reviewer_id = next(
            member["id"]
            for member in members
            if member["id"] != participant_id
        )
        return [
            {
                "title": "Conflicting sampling requirements",
                "summary": "The new setting conflicts with the existing baseline.",
                "conflict_type": "requirement_violation",
                "required_expertise": "Signal validation",
                "source_entry_ids": [
                    existing_entries[-1]["id"],
                    new_entries[0]["id"],
                ],
                "reviewer_ids": [reviewer_id],
                "participant_ids": [participant_id],
            }
        ]


@pytest.fixture()
def client(tmp_path: Path):
    service = FakeMistralService()
    store = JsonStore(
        tmp_path / "data",
        Path(__file__).resolve().parents[1] / "schemas",
    )
    app = create_app(
        service=service,
        store=store,
        test_config={"TESTING": True},
    )
    with app.test_client() as test_client:
        yield test_client, service


def signup(
    test_client,
    *,
    username: str = "maya",
    name: str = "Maya",
):
    response = test_client.post(
        "/api/signup",
        json={"username": username, "password": "test-password"},
    )
    assert response.status_code == 201
    profile = response.get_json()
    update = test_client.put(
        "/api/profiles/me",
        json={"content": {"name": name, "expertise": "Firmware"}},
    )
    assert update.status_code == 200
    return profile


def test_upload_creates_schema_backed_project_and_query_uses_its_id(client):
    test_client, service = client
    signup(test_client)
    upload = test_client.post(
        "/api/documents",
        data={"file": (BytesIO(b"fake pdf"), "protocol.pdf")},
        content_type="multipart/form-data",
    )

    assert upload.status_code == 201
    bundle = upload.get_json()
    project_id = bundle["project"]["id"]
    entry_id = bundle["entries"][0]["id"]
    assert project_id.startswith("prj_")
    assert entry_id.startswith("ir_")
    assert bundle["project"]["ir"] == [entry_id]
    assert bundle["document"]["page_count"] == 1
    assert "pages" not in bundle["document"]

    fetched = test_client.get(f"/api/projects/{project_id}")
    assert fetched.status_code == 200
    assert fetched.get_json()["entries"][0]["id"] == entry_id

    answer = test_client.post(
        f"/api/projects/{project_id}/questions",
        json={"question": "What is the sampling rate?", "history": []},
    )
    assert answer.status_code == 200
    payload = answer.get_json()
    assert payload["project_id"] == project_id
    assert payload["citations"][0]["entry_id"] == entry_id
    assert service.last_entries[0]["id"] == entry_id


def test_library_lists_uploaded_project(client):
    test_client, _service = client
    signup(test_client)
    test_client.post(
        "/api/documents",
        data={"file": (BytesIO(b"fake pdf"), "protocol.pdf")},
        content_type="multipart/form-data",
    )

    response = test_client.get("/api/documents")
    documents = response.get_json()["documents"]
    assert response.status_code == 200
    assert documents[0]["name"] == "protocol"
    assert documents[0]["entry_count"] == 1


def test_multiple_documents_append_entries_to_one_project(client):
    test_client, _service = client
    signup(test_client)
    project = test_client.post(
        "/api/projects",
        json={"name": "Combined evidence"},
    ).get_json()

    for filename in ("protocol.pdf", "results.pdf"):
        response = test_client.post(
            f"/api/projects/{project['id']}/documents",
            data={"file": (BytesIO(b"fake pdf"), filename)},
            content_type="multipart/form-data",
        )
        assert response.status_code == 201

    bundle = response.get_json()
    assert len(bundle["documents"]) == 2
    assert len(bundle["project"]["documents"]) == 2
    assert len(bundle["entries"]) == 2
    assert {
        entry["content"]["source"]["filename"]
        for entry in bundle["entries"]
    } == {"protocol.pdf", "results.pdf"}


def test_upload_rejects_unsupported_files(client):
    test_client, _service = client
    signup(test_client)
    response = test_client.post(
        "/api/documents",
        data={"file": (BytesIO(b"hello"), "notes.txt")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 415
    assert "PDF" in response.get_json()["error"]


def test_unknown_project_id_returns_404(client):
    test_client, _service = client
    signup(test_client)
    response = test_client.get("/api/projects/prj_doesnotexist")
    assert response.status_code == 404
    assert response.get_json()["error"] == "The requested resource was not found."


def test_profiles_projects_messages_views_and_changes(client):
    test_client, _service = client
    assert test_client.get("/api/projects").status_code == 401
    profile = signup(test_client)
    profile_id = profile["id"]
    assert "password_hash" not in profile

    project_response = test_client.post(
        "/api/projects",
        json={"name": "MedGuard", "creator_id": "user_attacker"},
    )
    assert project_response.status_code == 201
    project = project_response.get_json()
    assert project["users"] == [profile_id]
    assert project["admins"] == [profile_id]

    message_response = test_client.post(
        f"/api/projects/{project['id']}/messages",
        json={
            "text": "The debounce filter was enabled.",
            "author_id": "user_attacker",
        },
    )
    assert message_response.status_code == 201
    entry = message_response.get_json()["entries"][0]
    assert entry["author"] == profile_id

    view_response = test_client.get(
        f"/api/projects/{project['id']}/view",
        query_string={"user_id": profile_id},
    )
    assert view_response.status_code == 200
    claim = view_response.get_json()["claims"][0]
    assert claim["entry_id"] == entry["id"]
    assert claim["grounding"][0]["path"] == "content.statement"

    changes_response = test_client.get(
        f"/api/projects/{project['id']}/changes",
        query_string={"since": "2020-01-01T00:00:00+00:00"},
    )
    assert changes_response.status_code == 200
    assert changes_response.get_json()["entries"][0]["id"] == entry["id"]


def test_changes_create_grounded_assigned_conflict_issues(client):
    test_client, service = client
    creator = signup(test_client)
    project = test_client.post(
        "/api/projects",
        json={"name": "Automatic review"},
    ).get_json()
    first_change = test_client.post(
        f"/api/projects/{project['id']}/messages",
        json={"text": "The baseline requires a 1 kHz sampling rate."},
    ).get_json()["entries"][0]

    test_client.post("/api/logout")
    reviewer = signup(
        test_client,
        username="reviewer",
        name="Signal Reviewer",
    )
    test_client.post("/api/logout")
    test_client.post(
        "/api/login",
        json={"username": "maya", "password": "test-password"},
    )
    added = test_client.post(
        f"/api/projects/{project['id']}/members",
        json={"username": "reviewer"},
    )
    assert added.status_code == 200

    service.conflict_to_detect = True
    changed = test_client.post(
        f"/api/projects/{project['id']}/messages",
        json={"text": "The sampling rate was changed to 2 kHz."},
    )
    assert changed.status_code == 201
    payload = changed.get_json()
    assert payload["conflict_review"]["status"] == "complete"
    assert len(payload["conflict_review"]["created_issue_ids"]) == 1

    issues = test_client.get(
        f"/api/projects/{project['id']}/issues",
    ).get_json()["issues"]
    automatic_issue = issues[0]
    assert automatic_issue["origin"] == "automatic"
    assert automatic_issue["conflict_type"] == "requirement_violation"
    assert automatic_issue["participant_ids"] == [creator["id"]]
    assert automatic_issue["reviewer_ids"] == [reviewer["id"]]
    assert automatic_issue["source_entry_ids"] == [
        first_change["id"],
        payload["entries"][0]["id"],
    ]

    test_client.post("/api/logout")
    test_client.post(
        "/api/login",
        json={"username": "reviewer", "password": "test-password"},
    )
    reviewer_cannot_contribute = test_client.post(
        f"/api/projects/{project['id']}/issues/{automatic_issue['id']}/proposals",
        json={"solution": "Reviewers must remain independent."},
    )
    assert reviewer_cannot_contribute.status_code == 403


def test_change_is_preserved_when_automatic_review_is_unavailable(client):
    test_client, service = client
    signup(test_client)
    project = test_client.post(
        "/api/projects",
        json={"name": "Resilient review"},
    ).get_json()
    test_client.post(
        f"/api/projects/{project['id']}/messages",
        json={"text": "The first baseline was recorded."},
    )

    service.conflict_error = True
    response = test_client.post(
        f"/api/projects/{project['id']}/messages",
        json={"text": "The baseline changed."},
    )

    assert response.status_code == 201
    assert response.get_json()["conflict_review"]["status"] == "skipped"
    bundle = test_client.get(f"/api/projects/{project['id']}").get_json()
    assert len(bundle["entries"]) == 2


def test_login_profile_privacy_join_promotion_and_exit(client):
    test_client, _service = client
    admin = signup(test_client, username="admin", name="Admin")
    project = test_client.post(
        "/api/projects",
        json={"name": "Shared project"},
    ).get_json()

    test_client.post("/api/logout")
    member = signup(test_client, username="member", name="Member")
    assert test_client.get("/api/projects").get_json()["projects"] == []

    joined = test_client.post(
        f"/api/projects/{project['id']}/join",
    )
    assert joined.status_code == 200
    assert member["id"] in joined.get_json()["project"]["users"]

    forbidden = test_client.post(
        f"/api/projects/{project['id']}/promote",
        json={"user_id": member["id"], "caller_id": admin["id"]},
    )
    assert forbidden.status_code == 403

    test_client.post("/api/logout")
    login = test_client.post(
        "/api/login",
        json={"username": "admin", "password": "test-password"},
    )
    assert login.status_code == 200
    assert "password_hash" not in login.get_json()

    promoted = test_client.post(
        f"/api/projects/{project['id']}/promote",
        json={"user_id": member["id"], "caller_id": member["id"]},
    )
    assert promoted.status_code == 200
    assert member["id"] in promoted.get_json()["admins"]

    exited = test_client.post(
        f"/api/projects/{project['id']}/exit",
        json={"user_id": member["id"]},
    )
    assert exited.status_code == 200
    assert admin["id"] not in exited.get_json()["users"]

    profiles = test_client.get("/api/profiles").get_json()["profiles"]
    assert all("password_hash" not in profile for profile in profiles)


def test_admin_can_add_and_remove_project_members(client):
    test_client, _service = client
    admin = signup(test_client, username="admin", name="Admin")
    project = test_client.post(
        "/api/projects",
        json={"name": "Managed team"},
    ).get_json()

    test_client.post("/api/logout")
    member = signup(test_client, username="member", name="Member")
    test_client.post("/api/logout")
    test_client.post(
        "/api/login",
        json={"username": "admin", "password": "test-password"},
    )

    added = test_client.post(
        f"/api/projects/{project['id']}/members",
        json={"username": "member"},
    )
    assert added.status_code == 200
    assert member["id"] in added.get_json()["project"]["users"]

    removed = test_client.delete(
        f"/api/projects/{project['id']}/members/{member['id']}",
    )
    assert removed.status_code == 200
    assert removed.get_json()["project"]["users"] == [admin["id"]]


def test_issue_proposals_support_collaboration_and_independent_approval(client):
    test_client, _service = client
    creator = signup(test_client, username="creator", name="Creator")
    project = test_client.post(
        "/api/projects",
        json={"name": "Reviewed solutions"},
    ).get_json()

    accounts = {}
    for username, name in (
        ("reviewer", "Domain Expert"),
        ("contributor_one", "Contributor One"),
        ("contributor_two", "Contributor Two"),
    ):
        test_client.post("/api/logout")
        accounts[username] = signup(
            test_client,
            username=username,
            name=name,
        )

    test_client.post("/api/logout")
    test_client.post(
        "/api/login",
        json={"username": "creator", "password": "test-password"},
    )
    for username in accounts:
        added = test_client.post(
            f"/api/projects/{project['id']}/members",
            json={"username": username},
        )
        assert added.status_code == 200

    issue_response = test_client.post(
        f"/api/projects/{project['id']}/issues",
        json={
            "title": "Sensor false positives",
            "summary": "The debounce behavior needs a reviewed solution.",
            "required_expertise": "Signal processing",
            "reviewer_ids": [accounts["reviewer"]["id"]],
        },
    )
    assert issue_response.status_code == 201
    issue = issue_response.get_json()

    assigned_reviewer_removal = test_client.delete(
        f"/api/projects/{project['id']}/members/"
        f"{accounts['reviewer']['id']}",
    )
    assert assigned_reviewer_removal.status_code == 409

    test_client.post("/api/logout")
    test_client.post(
        "/api/login",
        json={"username": "reviewer", "password": "test-password"},
    )
    assigned_reviewer_exit = test_client.post(
        f"/api/projects/{project['id']}/exit",
    )
    assert assigned_reviewer_exit.status_code == 409

    test_client.post("/api/logout")
    test_client.post(
        "/api/login",
        json={"username": "contributor_one", "password": "test-password"},
    )
    proposal_response = test_client.post(
        f"/api/projects/{project['id']}/issues/{issue['id']}/proposals",
        json={"solution": "Use a 20 ms adaptive debounce window."},
    )
    assert proposal_response.status_code == 201
    proposal = proposal_response.get_json()["proposals"][0]

    test_client.post("/api/logout")
    test_client.post(
        "/api/login",
        json={"username": "contributor_two", "password": "test-password"},
    )
    revised = test_client.post(
        f"/api/projects/{project['id']}/issues/{issue['id']}/proposals/"
        f"{proposal['id']}/revisions",
        json={
            "solution": "Use a 20 ms adaptive window with a 5 ms floor.",
            "base_version": 1,
        },
    )
    assert revised.status_code == 200
    revised_proposal = revised.get_json()["proposals"][0]
    assert len(revised_proposal["versions"]) == 2
    assert len(revised_proposal["contributors"]) == 2

    stale_revision = test_client.post(
        f"/api/projects/{project['id']}/issues/{issue['id']}/proposals/"
        f"{proposal['id']}/revisions",
        json={"solution": "Stale edit", "base_version": 1},
    )
    assert stale_revision.status_code == 409

    submitted = test_client.post(
        f"/api/projects/{project['id']}/issues/{issue['id']}/proposals/"
        f"{proposal['id']}/submit",
    )
    assert submitted.status_code == 200

    self_review = test_client.post(
        f"/api/projects/{project['id']}/issues/{issue['id']}/proposals/"
        f"{proposal['id']}/review",
        json={"decision": "approved", "comment": "Looks good."},
    )
    assert self_review.status_code == 403

    test_client.post("/api/logout")
    test_client.post(
        "/api/login",
        json={"username": "reviewer", "password": "test-password"},
    )
    approved = test_client.post(
        f"/api/projects/{project['id']}/issues/{issue['id']}/proposals/"
        f"{proposal['id']}/review",
        json={"decision": "approved", "comment": "Validated."},
    )
    assert approved.status_code == 200
    resolved = approved.get_json()
    assert resolved["status"] == "resolved"
    assert resolved["approved_proposal_id"] == proposal["id"]

    bundle = test_client.get(f"/api/projects/{project['id']}").get_json()
    resolution = bundle["entries"][-1]
    assert resolution["author"] == accounts["reviewer"]["id"]
    assert resolution["content"]["source"]["kind"] == "issue"
    assert resolution["content"]["source"]["version"] == 2
    assert creator["id"] in bundle["project"]["users"]
