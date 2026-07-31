from flask import Blueprint, jsonify, request

from data import store
from .auth import current_profile, login_required

bp = Blueprint("projects", __name__)


@bp.get("/api/projects")
@login_required
def list_own_projects():
    return jsonify(store.projects_for_user(current_profile()["id"]))


@bp.get("/api/projects/<project_id>/invite")
@login_required
def preview_invite(project_id: str):
    """Minimal public-ish preview so someone following an invite link can see
    what they're joining. Deliberately not the full project — non-members must
    not see members or IR content until they join. The project id doubles as
    the invite token: it's a UUID4, so it can't be guessed, only shared."""
    project = store.get_project(project_id)
    if project is None:
        return jsonify({"error": "project not found"}), 404
    return jsonify({"id": project["id"], "name": project["name"]})


@bp.post("/api/projects")
@login_required
def create_project():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    project = store.create_project(name, creator_id=current_profile()["id"])
    return jsonify(project), 201


@bp.get("/api/projects/<project_id>")
@login_required
def get_project(project_id: str):
    project = store.get_project(project_id)
    if project is None:
        return jsonify({"error": "project not found"}), 404
    if current_profile()["id"] not in project["users"]:
        return jsonify({"error": "not a member of this project"}), 403
    return jsonify(project)


@bp.get("/api/projects/<project_id>/members")
@login_required
def list_members(project_id: str):
    """Member profiles (with admin flags) so the UI can show names, not ids."""
    project = store.get_project(project_id)
    if project is None:
        return jsonify({"error": "project not found"}), 404
    if current_profile()["id"] not in project["users"]:
        return jsonify({"error": "not a member of this project"}), 403

    members = []
    for user_id in project["users"]:
        profile = store.get_profile(user_id)
        if profile is not None:
            members.append(
                {**store.public_profile(profile), "is_admin": user_id in project["admins"]}
            )
    return jsonify(members)


@bp.post("/api/projects/<project_id>/join")
@login_required
def join_project(project_id: str):
    project = store.get_project(project_id)
    if project is None:
        return jsonify({"error": "project not found"}), 404

    # Joining only ever grants membership, never admin.
    store.add_member(project_id, current_profile()["id"])
    # Re-read: the project fetched above is a copy, so it doesn't reflect the write.
    return jsonify(store.get_project(project_id))


@bp.post("/api/projects/<project_id>/promote")
@login_required
def promote_member(project_id: str):
    project = store.get_project(project_id)
    if project is None:
        return jsonify({"error": "project not found"}), 404
    if current_profile()["id"] not in project["admins"]:
        return jsonify({"error": "only admins can promote members"}), 403

    user_id = (request.get_json(silent=True) or {}).get("user_id")
    if user_id not in project["users"]:
        return jsonify({"error": "that user is not a member of this project"}), 400

    store.promote_admin(project_id, user_id)
    return jsonify(store.get_project(project_id))


@bp.post("/api/projects/<project_id>/exit")
@login_required
def exit_project(project_id: str):
    project = store.get_project(project_id)
    if project is None:
        return jsonify({"error": "project not found"}), 404
    if current_profile()["id"] not in project["users"]:
        return jsonify({"error": "not a member of this project"}), 403

    remaining = store.remove_member(project_id, current_profile()["id"])
    # Project is gone once its last member leaves.
    return ("", 204) if remaining is None else jsonify(remaining)
