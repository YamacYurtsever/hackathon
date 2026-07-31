"""The read and write paths over a project's IR.

Read: `/view` re-projects the project for you, `/changes` reports what's new.
Write: `/input` proposes changes and stores nothing, `/document` does the same
for a file, and `/requests` submits the ones the author keeps — one request per
change — and only an admin can merge them. Nothing reaches the IR by any other
route.
"""

import os

from flask import Blueprint, jsonify, request

from ai import conflicts as conflict_detection
from ai import reprojection
from ai.documents import DocumentError, read_document
from ai.interpret import interpret_message
from ai.interpret.validate import clean_operation
from data import store
from .auth import current_profile, login_required

bp = Blueprint("pipeline", __name__)


def _check_for_conflicts(project_id: str, landed_ids: list[str]) -> None:
    """Looks for contradictions between what just landed and what was there.

    Called wherever the IR changes, which is the only moment it can start
    contradicting itself. Best-effort by design: a conflict we miss is found on
    the next merge, and a detector that fails should never fail a merge.
    """
    if not landed_ids:
        return

    entries = store.entries_for_project(project_id)
    landed = [entry for entry in entries if entry["id"] in set(landed_ids)]
    existing = [entry for entry in entries if entry["id"] not in set(landed_ids)]

    for pair in conflict_detection.find_conflicts(landed, existing):
        store.record_conflict(project_id, pair["a"], pair["b"], pair["reason"])


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


@bp.post("/api/projects/<project_id>/document")
@login_required
def project_document(project_id: str):
    """A file is a longer message, so it arrives where a message arrives and
    comes back the same way: proposed changes, nothing stored. A document is not
    a licence to write to the IR — it still passes both gates.

    The file itself is never kept. We take its text and its name; the bytes go
    out of scope when this returns."""
    project, error = _member_project(project_id)
    if project is None:
        return error

    uploaded = request.files.get("file")
    if uploaded is None or not (uploaded.filename or "").strip():
        return jsonify({"error": "a file is required"}), 400

    # Never touches the filesystem, so this is about what gets echoed back and
    # stored in a request's source text, not about path traversal.
    filename = os.path.basename(uploaded.filename)[:120]

    try:
        result = read_document(
            filename, uploaded.read(), existing=store.entries_for_project(project_id)
        )
    except DocumentError as refusal:
        # A refusal is a message to a person, not a stack trace: it says which
        # ceiling was hit and what to send instead.
        return jsonify({"error": str(refusal)}), 400

    return jsonify(result)


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

# Long enough to check a fact against, short enough to read in a queue.
_QUOTE_LIMIT = 300


def _source_text(raw: object, fallback: str) -> str:
    """What a reviewer is shown as the origin of one change.

    For a typed message that's the message. For a fact read out of a document
    it's the document, where in it, and the sentence that said so — otherwise
    checking one proposal means going back and re-reading the file.
    """
    provenance = raw.get("provenance") if isinstance(raw, dict) else None
    if not isinstance(provenance, dict):
        return fallback

    document = provenance.get("document")
    if not isinstance(document, str) or not document.strip():
        return fallback

    where = ", ".join(
        location
        for location in provenance.get("locations") or []
        if isinstance(location, str) and location.strip()
    )
    origin = f"{document.strip()}{f' — {where}' if where else ''}"

    quote = provenance.get("quote")
    if not isinstance(quote, str) or not quote.strip():
        return origin

    quote = quote.strip()
    if len(quote) > _QUOTE_LIMIT:
        quote = quote[:_QUOTE_LIMIT].rstrip() + "…"
    return f"{origin}: “{quote}”"


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
    # Provenance rides on the operation and is stripped from it by cleaning —
    # it isn't part of the fact. It becomes the request's source text, which is
    # where a reviewer looks for "where did this come from?".
    created = [
        store.create_request(project_id, author, _source_text(raw, source_text), operation)
        for raw, operation in zip(operations, cleaned)
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
            _check_for_conflicts(project_id, merged)
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
    _check_for_conflicts(project_id, [entry_id])
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


# --- conflicts ---
#
# Resolution edits or drops an entry that is already in the IR, which is a
# second way to write to it. That's a real departure from "merging is the only
# write", taken deliberately and narrowly: every route here is admin-only, the
# same guard merge has, and an admin's own change already lands the moment they
# confirm it. No gate is being opened that wasn't already open to this person.


def _conflict_for_admin(project_id: str, conflict_id: str) -> tuple[dict | None, tuple]:
    project, error = _member_project(project_id)
    if project is None:
        return None, error
    if current_profile()["id"] not in project["admins"]:
        return None, (jsonify({"error": "only admins can resolve conflicts"}), 403)

    conflict = store.get_conflict(conflict_id)
    if conflict is None or conflict["project_id"] != project_id:
        return None, (jsonify({"error": "conflict not found"}), 404)
    return conflict, ()


def _settle_if_resolved(project_id: str, conflict: dict) -> bool:
    """Re-reads the two entries and drops the conflict only if it's really gone.

    An edit that doesn't resolve the contradiction shouldn't clear the flag —
    otherwise "resolving" a conflict is just closing the dialog.
    """
    entries = {entry["id"]: entry for entry in store.entries_for_project(project_id)}
    sides = [entries.get(entry_id) for entry_id in conflict["entry_ids"]]
    if any(side is None for side in sides):
        store.resolve_conflict(conflict["id"])
        return True

    still = conflict_detection.find_conflicts(sides[:1], sides[1:])
    if not still:
        store.resolve_conflict(conflict["id"])
        return True
    return False


@bp.get("/api/projects/<project_id>/conflicts")
@login_required
def list_conflicts(project_id: str):
    """Visible to every member. Everyone should know the record currently
    contradicts itself; only an admin can do anything about it."""
    project, error = _member_project(project_id)
    if project is None:
        return error
    return jsonify(store.conflicts_for_project(project_id))


@bp.put("/api/projects/<project_id>/conflicts/<conflict_id>/entries/<entry_id>")
@login_required
def edit_conflicting_entry(project_id: str, conflict_id: str, entry_id: str):
    """Correct one side. The fact stays its author's — an admin settling a
    contradiction isn't claiming it."""
    conflict, error = _conflict_for_admin(project_id, conflict_id)
    if conflict is None:
        return error
    if entry_id not in conflict["entry_ids"]:
        return jsonify({"error": "that entry isn't part of this conflict"}), 400

    content = (request.get_json(silent=True) or {}).get("content")
    if not isinstance(content, dict) or not str(content.get("statement", "")).strip():
        return jsonify({"error": "content needs a statement"}), 400

    if store.update_entry_content(entry_id, content) is None:
        return jsonify({"error": "entry not found"}), 404

    reprojection.invalidate_project(project_id)
    return jsonify({"resolved": _settle_if_resolved(project_id, conflict)})


@bp.post("/api/projects/<project_id>/conflicts/<conflict_id>/discard/<entry_id>")
@login_required
def discard_conflicting_entry(project_id: str, conflict_id: str, entry_id: str):
    """Drop one side entirely. The only place the IR loses a fact, which is why
    it needs the same admin gate merging does."""
    conflict, error = _conflict_for_admin(project_id, conflict_id)
    if conflict is None:
        return error
    if entry_id not in conflict["entry_ids"]:
        return jsonify({"error": "that entry isn't part of this conflict"}), 400

    store.remove_entry(project_id, entry_id)
    reprojection.invalidate_project(project_id)
    return jsonify({"resolved": True})


@bp.post("/api/projects/<project_id>/conflicts/<conflict_id>/dismiss")
@login_required
def dismiss_conflict(project_id: str, conflict_id: str):
    """"These don't actually contradict." Kept rather than deleted, so the next
    merge doesn't raise the same pair and make the ruling meaningless."""
    conflict, error = _conflict_for_admin(project_id, conflict_id)
    if conflict is None:
        return error

    store.dismiss_conflict(conflict_id)
    return "", 204
