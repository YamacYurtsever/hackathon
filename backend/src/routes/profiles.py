from flask import Blueprint, jsonify, request

from data import store
from .auth import current_profile, login_required

bp = Blueprint("profiles", __name__)


@bp.get("/api/profiles/<profile_id>")
@login_required
def get_profile(profile_id: str):
    profile = store.get_profile(profile_id)
    if profile is None:
        return jsonify({"error": "profile not found"}), 404
    return jsonify(store.public_profile(profile))


@bp.put("/api/profiles/me")
@login_required
def update_own_profile():
    body = request.get_json(silent=True) or {}
    content = body.get("content")
    if not isinstance(content, dict):
        return jsonify({"error": "content must be an object"}), 400

    updated = store.update_profile_content(current_profile()["id"], content)
    return jsonify(store.public_profile(updated))
