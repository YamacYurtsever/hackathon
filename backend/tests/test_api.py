from io import BytesIO
from pathlib import Path

import pytest

from app import create_app
from storage import JsonStore


class FakeMistralService:
    configured = True

    def __init__(self) -> None:
        self.last_entries = []

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


def test_upload_creates_schema_backed_project_and_query_uses_its_id(client):
    test_client, service = client
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


def test_upload_rejects_unsupported_files(client):
    test_client, _service = client
    response = test_client.post(
        "/api/documents",
        data={"file": (BytesIO(b"hello"), "notes.txt")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 415
    assert "PDF" in response.get_json()["error"]


def test_unknown_project_id_returns_404(client):
    test_client, _service = client
    response = test_client.get("/api/projects/prj_doesnotexist")
    assert response.status_code == 404
    assert response.get_json()["error"] == "That project ID was not found."
