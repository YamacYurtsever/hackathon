from functools import wraps

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from data import store

bp = Blueprint("auth", __name__)

SESSION_KEY = "profile_id"


def current_profile() -> dict | None:
    profile_id = session.get(SESSION_KEY)
    return store.get_profile(profile_id) if profile_id else None


def login_required(view):
    """Reject anonymous callers; the acting user always comes from the session,
    never from a client-supplied id."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_profile() is None:
            return jsonify({"error": "authentication required"}), 401
        return view(*args, **kwargs)

    return wrapped


@bp.post("/api/signup")
def signup():
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400
    if store.find_profile_by_username(username):
        return jsonify({"error": "username already taken"}), 409

    # content starts empty — the user describes themselves from the app later.
    profile = store.create_profile(username, generate_password_hash(password), {})
    session[SESSION_KEY] = profile["id"]
    return jsonify(store.public_profile(profile)), 201


@bp.post("/api/login")
def login():
    body = request.get_json(silent=True) or {}
    profile = store.find_profile_by_username((body.get("username") or "").strip())

    if profile is None or not check_password_hash(
        profile["password_hash"], body.get("password") or ""
    ):
        return jsonify({"error": "invalid username or password"}), 401

    session[SESSION_KEY] = profile["id"]
    return jsonify(store.public_profile(profile))


@bp.post("/api/logout")
def logout():
    session.pop(SESSION_KEY, None)
    return "", 204


@bp.get("/api/me")
def me():
    profile = current_profile()
    if profile is None:
        return jsonify({"error": "authentication required"}), 401
    return jsonify(store.public_profile(profile))
