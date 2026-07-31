"""The read and write paths over a project's IR.

Read: `/view` re-projects the project for you, `/changes` reports what's new.
Write: `/input` proposes a changeset, `/requests` stores it once you confirm,
and only an admin can apply it. Nothing reaches the IR by any other route.
"""

from flask import Blueprint, jsonify, request

import reprojection
import store
from auth import current_profile, login_required
from extraction.classify import classify
from extraction.extract import extract_changeset
from extraction.validate import validate_operation

bp = Blueprint("pipeline", __name__)


def _member_project(project_id: str) -> tuple[dict | None, tuple]:
    """Loads a project the caller is a member of, or the error to return."""
    project = store.get_project(project_id)
    if project is None:
        return None, (jsonify({"error": "project not found"}), 404)
    if current_profile()["id"] not in project["users"]:
        return None, (jsonify({"error": "not a member of this project"}), 403)
    return project, ()


@bp.post("/api/projects/<project_id>/input")
@login_required
def project_input(project_id: str):
    """One endpoint behind the single input box. Nothing is stored here — a
    statement comes back as a proposed changeset for the author to confirm."""
    project, error = _member_project(project_id)
    if project is None:
        return error

    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400

    profile = current_profile()
    entries = store.entries_for_project(project_id)

    # An explicit override from the UI's "treat it as the other thing" wins over
    # the classifier.
    kind = body.get("kind")
    if kind not in ("changeset", "answer"):
        kind = "changeset" if classify(text) == "statement" else "answer"

    if kind == "answer":
        result = reprojection.answer(text, entries, profile)
        return jsonify({"kind": "answer", "text": text, **result})

    changeset = extract_changeset(text, profile=profile, existing=entries)
    return jsonify({"kind": "changeset", "text": text, **changeset})


@bp.get("/api/projects/<project_id>/view")
@login_required
def project_view(project_id: str):
    """The project re-projected for whoever is asking."""
    project, error = _member_project(project_id)
    if project is None:
        return error

    entries = store.entries_for_project(project_id)
    if not entries:
        return jsonify({"segments": [], "cached": False})

    return jsonify(
        reprojection.cached_summary(
            project_id, current_profile()["id"], entries, current_profile()
        )
    )


@bp.get("/api/projects/<project_id>/changes")
@login_required
def project_changes(project_id: str):
    """Entries touched since a timestamp — an updated entry counts, since
    applying an update refreshes its `created_at`."""
    project, error = _member_project(project_id)
    if project is None:
        return error

    # A "+00:00" offset arrives as " 00:00" if the client didn't encode it, and
    # the string compare then quietly returns everything.
    since = (request.args.get("since") or "").replace(" ", "+")
    entries = store.entries_for_project(project_id)
    if since:
        entries = [entry for entry in entries if entry["created_at"] > since]

    return jsonify(entries)


# --- write path ---


@bp.post("/api/projects/<project_id>/requests")
@login_required
def create_request(project_id: str):
    """The author confirms a changeset. First point anything is persisted, and
    always a request — being an admin doesn't skip the queue."""
    project, error = _member_project(project_id)
    if project is None:
        return error

    body = request.get_json(silent=True) or {}
    operations = body.get("operations")
    if not isinstance(operations, list) or not operations:
        return jsonify({"error": "operations must be a non-empty list"}), 400

    created = store.create_request(
        project_id,
        author=current_profile()["id"],
        source_text=(body.get("text") or "").strip(),
        operations=operations,
    )
    return jsonify(created), 201


@bp.get("/api/projects/<project_id>/requests")
@login_required
def list_requests(project_id: str):
    """Visible to every member — pending changes shouldn't be a private queue."""
    project, error = _member_project(project_id)
    if project is None:
        return error
    return jsonify(store.requests_for_project(project_id))


@bp.put("/api/projects/<project_id>/requests/<request_id>")
@login_required
def edit_request(project_id: str, request_id: str):
    """Hand-edit a pending request: its author fixing our reading, or an admin
    fixing a small error instead of rejecting the whole thing."""
    project, error = _member_project(project_id)
    if project is None:
        return error

    pending = store.get_request(request_id)
    if pending is None or pending["project_id"] != project_id:
        return jsonify({"error": "request not found"}), 404

    user_id = current_profile()["id"]
    if user_id != pending["author"] and user_id not in project["admins"]:
        return jsonify({"error": "only the author or an admin can edit this"}), 403

    operations = (request.get_json(silent=True) or {}).get("operations")
    if not isinstance(operations, list) or not operations:
        return jsonify({"error": "operations must be a non-empty list"}), 400

    # Hand-edits skip the model, so they skip its validation too — check them
    # the same way, or the editable path becomes a hole in the guardrail.
    entry_ids = set(project["ir"])
    problems = [
        problem
        for operation in operations
        for problem in validate_operation(operation, pending["source_text"], entry_ids)
    ]
    if problems:
        return jsonify({"error": "invalid operations", "problems": problems}), 400

    return jsonify(store.update_request_operations(request_id, operations))


@bp.post("/api/projects/<project_id>/requests/<request_id>/approve")
@login_required
def approve_request(project_id: str, request_id: str):
    """Admin only, no exceptions — this is the only way the IR changes."""
    project, error = _member_project(project_id)
    if project is None:
        return error
    if current_profile()["id"] not in project["admins"]:
        return jsonify({"error": "only admins can approve requests"}), 403

    pending = store.get_request(request_id)
    if pending is None or pending["project_id"] != project_id:
        return jsonify({"error": "request not found"}), 404

    affected, failure = store.apply_request(request_id)
    if failure:
        return jsonify({"error": failure}), 409

    # Entries changed, so every cached summary of this project is stale.
    reprojection.invalidate_project(project_id)
    return jsonify({"applied": affected})


@bp.post("/api/projects/<project_id>/requests/<request_id>/reject")
@login_required
def reject_request(project_id: str, request_id: str):
    """Rejecting deletes it — a rejected proposal isn't a fact."""
    project, error = _member_project(project_id)
    if project is None:
        return error
    if current_profile()["id"] not in project["admins"]:
        return jsonify({"error": "only admins can reject requests"}), 403

    pending = store.get_request(request_id)
    if pending is None or pending["project_id"] != project_id:
        return jsonify({"error": "request not found"}), 404

    store.delete_request(request_id)
    return "", 204
