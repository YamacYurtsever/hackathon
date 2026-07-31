"""The read and write paths over a project's IR.

Read: `/view` re-projects the project for you, `/changes` reports what's new.
Write: `/input` proposes changes and stores nothing, `/requests` submits the
ones the author keeps — one request per change — and only an admin can merge
them. Nothing reaches the IR by any other route.
"""

from flask import Blueprint, jsonify, request

from ai import reprojection
from ai.interpret import interpret_message
from ai.interpret.validate import clean_operation
from data import store
from .auth import current_profile, login_required

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
    message comes back as proposed changes for the author to review, plus an
    answer if it asked something. It can be both."""
    project, error = _member_project(project_id)
    if project is None:
        return error

    text = ((request.get_json(silent=True) or {}).get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400

    entries = store.entries_for_project(project_id)
    result = interpret_message(text, profile=current_profile(), existing=entries)

    # Reading the message tells us *whether* something was asked; re-projecting
    # answers it properly — in the asker's terms, with the entries it drew on,
    # and through the same citation check the summary goes through. An answer
    # without sources is the one bit of prose here nobody could trace.
    if result["answer"]:
        grounded = reprojection.answer(text, entries, current_profile())
        result["answer_segments"] = grounded["segments"]

    return jsonify({"text": text, **result})


@bp.get("/api/projects/<project_id>/view")
@login_required
def project_view(project_id: str):
    """The project re-projected for whoever is asking."""
    project, error = _member_project(project_id)
    if project is None:
        return error

    entries = store.entries_for_project(project_id)
    if not entries:
        # Nothing to summarize, but the reader is still someone in particular —
        # orient them in their own terms rather than showing a blank panel.
        greeting = reprojection.cached_welcome(
            current_profile()["id"], current_profile()
        )
        return jsonify(
            {
                "segments": [],
                "welcome": greeting["text"],
                "cached": greeting["cached"],
            }
        )

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
def submit_requests(project_id: str):
    """The author submits proposed changes for review. Submitting is not
    approving — nothing reaches the IR until an admin merges it. Each change
    becomes its own request, so one can be merged and another rejected."""
    project, error = _member_project(project_id)
    if project is None:
        return error

    body = request.get_json(silent=True) or {}
    operations = body.get("operations")
    if not isinstance(operations, list) or not operations:
        return jsonify({"error": "operations must be a non-empty list"}), 400

    entry_ids = set(project["ir"])
    cleaned = [clean_operation(operation, entry_ids) for operation in operations]
    if any(operation is None for operation in cleaned):
        return jsonify({"error": "one or more operations are invalid"}), 400

    source_text = (body.get("text") or "").strip()
    author = current_profile()["id"]
    created = [
        store.create_request(project_id, author, source_text, operation)
        for operation in cleaned
    ]

    # An admin submitting their own change has already made the only decision
    # gate 2 exists to capture — asking them to merge what they just confirmed
    # is a dialog that only ever gets one answer. It still goes through
    # create-then-merge rather than writing directly, so merging stays the one
    # path into the IR and authorship is assigned exactly as before.
    if author in project["admins"]:
        merged, still_pending = [], []
        for pending in created:
            entry_id, failure = store.merge_request(pending["id"])
            (still_pending if failure else merged).append(
                pending if failure else entry_id
            )
        if merged:
            reprojection.invalidate_project(project_id)
        return jsonify({"requests": still_pending, "merged": merged}), 201

    return jsonify({"requests": created, "merged": []}), 201


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

    # Hand-edits skip the model, so they skip its checks too — run them through
    # the same ones, or the editable path becomes a hole in the guardrail.
    operation = clean_operation(
        (request.get_json(silent=True) or {}).get("operation"), set(project["ir"])
    )
    if operation is None:
        return jsonify({"error": "operation is invalid"}), 400

    return jsonify(store.update_request_operation(request_id, operation))


@bp.post("/api/projects/<project_id>/requests/<request_id>/merge")
@login_required
def merge_request(project_id: str, request_id: str):
    """Admin only, no exceptions — merging is the only way the IR changes."""
    project, error = _member_project(project_id)
    if project is None:
        return error
    if current_profile()["id"] not in project["admins"]:
        return jsonify({"error": "only admins can merge requests"}), 403

    pending = store.get_request(request_id)
    if pending is None or pending["project_id"] != project_id:
        return jsonify({"error": "request not found"}), 404

    entry_id, failure = store.merge_request(request_id)
    if failure:
        return jsonify({"error": failure}), 409

    # Entries changed, so every cached summary of this project is stale.
    reprojection.invalidate_project(project_id)
    return jsonify({"merged": entry_id})


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
