import mimetypes
import os
from functools import wraps
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify, request, session
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from mistral_service import (
    MistralConfigurationError,
    MistralDocumentService,
    MistralProcessingError,
)
from seed import seed_medguard
from storage import (
    JsonStore,
    PermissionDeniedError,
    RecordNotFoundError,
    StoreConflictError,
)

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

MAX_FILE_BYTES = 20 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
    ".pptx": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    ),
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".avif": "image/avif",
}


def create_app(
    *,
    service: MistralDocumentService | None = None,
    store: JsonStore | None = None,
    test_config: dict[str, Any] | None = None,
) -> Flask:
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=MAX_FILE_BYTES,
        JSON_SORT_KEYS=False,
        SECRET_KEY=os.environ.get(
            "FLASK_SECRET_KEY",
            "development-only-change-me",
        ),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)
    CORS(
        app,
        origins=[
            os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173"),
            os.environ.get("FRONTEND_ORIGIN_IP", "http://127.0.0.1:5173"),
        ],
        supports_credentials=True,
    )

    document_service = service or MistralDocumentService(
        os.environ.get("MISTRAL_API_KEY", ""),
        ocr_model=os.environ.get("MISTRAL_OCR_MODEL", "mistral-ocr-latest"),
        chat_model=os.environ.get(
            "MISTRAL_CHAT_MODEL",
            "mistral-small-latest",
        ),
    )
    json_store = store or JsonStore(
        Path(os.environ.get("DATA_DIR", BASE_DIR / "data")),
        BASE_DIR / "schemas",
    )
    app.extensions["document_service"] = document_service
    app.extensions["json_store"] = json_store

    def current_user_id() -> str | None:
        profile_id = session.get("profile_id")
        if not isinstance(profile_id, str):
            return None
        try:
            json_store.get_profile(profile_id)
        except RecordNotFoundError:
            session.pop("profile_id", None)
            return None
        return profile_id

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if current_user_id() is None:
                return _error("Authentication required.", 401)
            return view(*args, **kwargs)

        return wrapped

    def require_project_member(project_id: str) -> dict[str, Any]:
        project = json_store.get_project(project_id)
        if current_user_id() not in project["users"]:
            raise PermissionDeniedError(
                "Only project members can access this project."
            )
        return project

    def project_bundle(project_id: str) -> dict[str, Any]:
        require_project_member(project_id)
        bundle = json_store.get_bundle(project_id)
        bundle["members"] = [
            json_store.get_profile(profile_id)
            for profile_id in bundle["project"]["users"]
        ]
        return bundle

    def ingest_document(project_id: str | None = None):
        if project_id is not None:
            require_project_member(project_id)

        uploaded_file = request.files.get("file")
        if uploaded_file is None:
            return _error("Attach a file in the 'file' field.", 400)

        filename = secure_filename(uploaded_file.filename or "")
        extension = Path(filename).suffix.casefold()
        if not filename or extension not in ALLOWED_EXTENSIONS:
            return _error(
                "Use a PDF, DOCX, PPTX, PNG, JPG, WEBP, or AVIF file.",
                415,
            )

        content = uploaded_file.read()
        if not content:
            return _error("The uploaded file is empty.", 400)
        if len(content) > MAX_FILE_BYTES:
            return _error("Files must be 20 MB or smaller.", 413)

        guessed_type = ALLOWED_EXTENSIONS[extension]
        supplied_type = uploaded_file.mimetype
        mime_type = (
            supplied_type
            if supplied_type
            and supplied_type != "application/octet-stream"
            else guessed_type
        )
        if mime_type not in set(ALLOWED_EXTENSIONS.values()):
            mime_type = mimetypes.guess_type(filename)[0] or guessed_type

        result = document_service.process_document(content, mime_type)
        document_args = {
            "filename": filename,
            "mime_type": mime_type,
            "size_bytes": len(content),
            "pages": result["pages"],
            "facts": result["facts"],
            "ocr_model": result["ocr_model"],
            "chat_model": result["chat_model"],
        }
        if project_id is None:
            bundle = json_store.create_document(
                **document_args,
                creator_id=current_user_id(),
            )
        else:
            bundle = json_store.add_document(
                project_id,
                **document_args,
                author_id=current_user_id(),
            )
        bundle["members"] = [
            json_store.get_profile(profile_id)
            for profile_id in bundle["project"]["users"]
        ]
        return jsonify(bundle), 201

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "mistral_configured": document_service.configured,
        }

    @app.post("/api/signup")
    def signup():
        payload = _json_object()
        username = payload.get("username")
        password = payload.get("password")
        if not isinstance(username, str) or not username.strip():
            return _error("Username is required.", 400)
        if len(username.strip()) > 80:
            return _error("Username must be 80 characters or fewer.", 400)
        if not isinstance(password, str) or len(password) < 8:
            return _error("Password must be at least 8 characters.", 400)
        profile = json_store.create_profile(
            {},
            username=username,
            password_hash=generate_password_hash(password),
        )
        session.clear()
        session["profile_id"] = profile["id"]
        return jsonify(profile), 201

    @app.post("/api/login")
    def login():
        payload = _json_object()
        username = payload.get("username")
        password = payload.get("password")
        profile = (
            json_store.find_profile_by_username(username)
            if isinstance(username, str)
            else None
        )
        if (
            profile is None
            or not isinstance(password, str)
            or not isinstance(profile.get("password_hash"), str)
            or not check_password_hash(profile["password_hash"], password)
        ):
            return _error("Invalid username or password.", 401)
        session.clear()
        session["profile_id"] = profile["id"]
        return json_store.get_profile(profile["id"])

    @app.post("/api/logout")
    def logout():
        session.clear()
        return "", 204

    @app.get("/api/me")
    @login_required
    def me():
        return json_store.get_profile(current_user_id())

    @app.get("/api/documents")
    @login_required
    def list_documents():
        return {
            "documents": json_store.list_documents(current_user_id())
        }

    @app.post("/api/documents")
    @login_required
    def create_document():
        return ingest_document()

    @app.get("/profiles")
    @app.get("/api/profiles")
    @login_required
    def list_profiles():
        return {"profiles": json_store.list_profiles()}

    @app.get("/profiles/<profile_id>")
    @app.get("/api/profiles/<profile_id>")
    @login_required
    def get_profile(profile_id: str):
        return json_store.get_profile(profile_id)

    @app.put("/api/profiles/me")
    @login_required
    def update_own_profile():
        payload = _json_object()
        content = payload.get("content")
        if not isinstance(content, dict):
            return _error("Profile content must be an object.", 400)
        return json_store.update_profile_content(
            current_user_id(),
            content,
        )

    @app.get("/projects")
    @app.get("/api/projects")
    @login_required
    def list_projects():
        return {
            "projects": json_store.list_projects(current_user_id())
        }

    @app.post("/projects")
    @app.post("/api/projects")
    @login_required
    def create_project():
        payload = _json_object()
        name = payload.get("name")
        if not isinstance(name, str) or not name.strip():
            return _error("Project name is required.", 400)
        project = json_store.create_project(name, current_user_id())
        return jsonify(project), 201

    @app.get("/projects/<project_id>")
    @app.get("/api/projects/<project_id>")
    @login_required
    def get_project(project_id: str):
        return project_bundle(project_id)

    @app.post("/projects/<project_id>/join")
    @app.post("/api/projects/<project_id>/join")
    @login_required
    def join_project(project_id: str):
        json_store.join_project(project_id, current_user_id())
        return project_bundle(project_id)

    @app.post("/api/projects/<project_id>/members")
    @login_required
    def add_project_member(project_id: str):
        payload = _json_object()
        user_id = payload.get("user_id")
        username = payload.get("username")
        if not isinstance(user_id, str):
            profile = (
                json_store.find_profile_by_username(username)
                if isinstance(username, str)
                else None
            )
            if profile is None:
                raise RecordNotFoundError(str(username))
            user_id = profile["id"]
        json_store.add_member(
            project_id,
            current_user_id(),
            user_id,
        )
        return project_bundle(project_id)

    @app.delete("/api/projects/<project_id>/members/<user_id>")
    @login_required
    def remove_project_member(project_id: str, user_id: str):
        json_store.remove_member(
            project_id,
            current_user_id(),
            user_id,
        )
        return project_bundle(project_id)

    @app.post("/api/projects/<project_id>/documents")
    @login_required
    def add_project_document(project_id: str):
        return ingest_document(project_id)

    @app.get("/api/projects/<project_id>/issues")
    @login_required
    def list_project_issues(project_id: str):
        return {
            "issues": json_store.list_issues(
                project_id,
                current_user_id(),
            )
        }

    @app.post("/api/projects/<project_id>/issues")
    @login_required
    def create_project_issue(project_id: str):
        payload = _json_object()
        title = _required_text(payload, "title", 160)
        summary = _required_text(payload, "summary", 1200)
        expertise = _required_text(payload, "required_expertise", 300)
        reviewer_ids = payload.get("reviewer_ids")
        if (
            not isinstance(reviewer_ids, list)
            or not all(isinstance(value, str) for value in reviewer_ids)
        ):
            return _error("reviewer_ids must be a list of user IDs.", 400)
        issue = json_store.create_issue(
            project_id,
            title=title,
            summary=summary,
            required_expertise=expertise,
            reviewer_ids=reviewer_ids,
            creator_id=current_user_id(),
        )
        return jsonify(issue), 201

    @app.post(
        "/api/projects/<project_id>/issues/<issue_id>/proposals"
    )
    @login_required
    def create_issue_proposal(project_id: str, issue_id: str):
        solution = _required_text(_json_object(), "solution", 5000)
        issue = json_store.create_proposal(
            project_id,
            issue_id,
            solution,
            current_user_id(),
        )
        return jsonify(issue), 201

    @app.post(
        "/api/projects/<project_id>/issues/<issue_id>/proposals/"
        "<proposal_id>/revisions"
    )
    @login_required
    def revise_issue_proposal(
        project_id: str,
        issue_id: str,
        proposal_id: str,
    ):
        payload = _json_object()
        solution = _required_text(payload, "solution", 5000)
        base_version = payload.get("base_version")
        if type(base_version) is not int or base_version < 1:
            return _error("base_version must be a positive integer.", 400)
        return json_store.revise_proposal(
            project_id,
            issue_id,
            proposal_id,
            solution,
            base_version,
            current_user_id(),
        )

    @app.post(
        "/api/projects/<project_id>/issues/<issue_id>/proposals/"
        "<proposal_id>/submit"
    )
    @login_required
    def submit_issue_proposal(
        project_id: str,
        issue_id: str,
        proposal_id: str,
    ):
        return json_store.submit_proposal(
            project_id,
            issue_id,
            proposal_id,
            current_user_id(),
        )

    @app.post(
        "/api/projects/<project_id>/issues/<issue_id>/proposals/"
        "<proposal_id>/review"
    )
    @login_required
    def review_issue_proposal(
        project_id: str,
        issue_id: str,
        proposal_id: str,
    ):
        payload = _json_object()
        decision = payload.get("decision")
        comment = payload.get("comment", "")
        if decision not in {"approved", "rejected"}:
            return _error("decision must be 'approved' or 'rejected'.", 400)
        if not isinstance(comment, str) or len(comment) > 1200:
            return _error("comment must be 1,200 characters or fewer.", 400)
        return json_store.review_proposal(
            project_id,
            issue_id,
            proposal_id,
            reviewer_id=current_user_id(),
            decision=decision,
            comment=comment,
        )

    @app.post("/projects/<project_id>/messages")
    @app.post("/api/projects/<project_id>/messages")
    @login_required
    def post_message(project_id: str):
        payload = _json_object()
        text = payload.get("text") or payload.get("message")
        if not isinstance(text, str) or not text.strip():
            return _error("Message text is required.", 400)
        if len(text) > 10_000:
            return _error("Message must be 10,000 characters or fewer.", 400)

        require_project_member(project_id)
        author_id = current_user_id()
        profile = json_store.get_profile(author_id)
        facts = document_service.extract_message(
            text.strip(),
            profile["content"],
        )
        entries = json_store.append_entries(project_id, facts, author_id)
        return jsonify({"entries": entries}), 201

    @app.get("/projects/<project_id>/view")
    @app.get("/api/projects/<project_id>/view")
    @login_required
    def get_personalized_view(project_id: str):
        user_id = request.args.get("user_id", "")
        if not user_id:
            user_id = current_user_id()
        bundle = project_bundle(project_id)
        if user_id not in bundle["project"]["users"]:
            raise PermissionDeniedError(
                "Only project members can request a personalized view."
            )
        profile = json_store.get_profile(user_id)
        claims = document_service.reproject_entries(
            bundle["entries"],
            profile["content"],
        )
        return {
            "project_id": project_id,
            "viewer": profile,
            "claims": claims,
        }

    @app.get("/projects/<project_id>/changes")
    @app.get("/api/projects/<project_id>/changes")
    @login_required
    def get_changes(project_id: str):
        since = request.args.get("since", "")
        if not since:
            return _error("since query parameter is required.", 400)
        require_project_member(project_id)
        entries = json_store.get_changes(project_id, since)
        return {
            "project_id": project_id,
            "since": since,
            "entries": entries,
        }

    @app.post("/projects/<project_id>/promote")
    @app.post("/api/projects/<project_id>/promote")
    @login_required
    def promote_member(project_id: str):
        payload = _json_object()
        user_id = payload.get("user_id")
        if not isinstance(user_id, str):
            return _error("user_id is required.", 400)
        return json_store.promote_member(
            project_id,
            current_user_id(),
            user_id,
        )

    @app.post("/projects/<project_id>/exit")
    @app.post("/api/projects/<project_id>/exit")
    @login_required
    def exit_project(project_id: str):
        return json_store.exit_project(
            project_id,
            current_user_id(),
        )

    @app.get("/api/entries/<entry_id>/versions")
    @login_required
    def get_entry_versions(entry_id: str):
        project = json_store.get_entry_project(entry_id)
        if current_user_id() not in project["users"]:
            raise PermissionDeniedError(
                "Only project members can view entry history."
            )
        return {
            "entry_id": entry_id,
            "versions": json_store.get_versions(entry_id),
        }

    @app.post("/api/projects/<project_id>/questions")
    @login_required
    def ask_project(project_id: str):
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return _error("Request body must be a JSON object.", 400)
        question = payload.get("question")
        if not isinstance(question, str) or not question.strip():
            return _error("Question is required.", 400)
        if len(question) > 2000:
            return _error("Question must be 2,000 characters or fewer.", 400)

        history = payload.get("history", [])
        if not isinstance(history, list):
            return _error("History must be a list.", 400)

        bundle = project_bundle(project_id)
        answer = document_service.answer_question(
            question.strip(),
            bundle["entries"],
            history,
        )
        return {
            **answer,
            "project_id": project_id,
        }

    @app.errorhandler(RecordNotFoundError)
    def handle_not_found(_error_value):
        return _error("The requested resource was not found.", 404)

    @app.errorhandler(PermissionDeniedError)
    def handle_permission_error(error):
        return _error(str(error), 403)

    @app.errorhandler(StoreConflictError)
    def handle_conflict_error(error):
        return _error(str(error), 409)

    @app.errorhandler(ValueError)
    def handle_value_error(error):
        return _error(str(error), 400)

    @app.errorhandler(MistralConfigurationError)
    def handle_configuration_error(error):
        return _error(str(error), 503)

    @app.errorhandler(MistralProcessingError)
    def handle_processing_error(error):
        return _error(str(error), 422)

    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(_error_value):
        return _error("Files must be 20 MB or smaller.", 413)

    @app.errorhandler(500)
    def handle_server_error(_error_value):
        return _error("Something went wrong on the server.", 500)

    return app


def _error(message: str, status: int):
    return jsonify({"error": message}), status


def _json_object() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")
    return payload


def _required_text(
    payload: dict[str, Any],
    key: str,
    maximum_length: int,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required.")
    if len(value.strip()) > maximum_length:
        raise ValueError(
            f"{key} must be {maximum_length:,} characters or fewer."
        )
    return value.strip()


app = create_app()

# The demo data is idempotent and is seeded only for the runnable application.
# Factory-created test applications remain isolated.
seed_medguard(app.extensions["json_store"])

if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
