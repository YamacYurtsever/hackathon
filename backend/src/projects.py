from flask import Blueprint, jsonify, request

import store
from auth import current_profile, login_required

bp = Blueprint("projects", __name__)


@bp.get("/api/projects")
@login_required
def list_own_projects():
    return jsonify(store.projects_for_user(current_profile()["id"]))


@bp.get("/api/projects/available")
@login_required
def list_available_projects():
    """Projects the caller could join — everything they're not already in."""
    return jsonify(store.projects_without_user(current_profile()["id"]))


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


@bp.post("/api/projects/<project_id>/join")
@login_required
def join_project(project_id: str):
    project = store.get_project(project_id)
    if project is None:
        return jsonify({"error": "project not found"}), 404

    # Joining only ever grants membership, never admin.
    store.add_member(project_id, current_profile()["id"])
    return jsonify(project)
