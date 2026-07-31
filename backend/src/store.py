import uuid
from datetime import datetime, timezone

profiles: dict[str, dict] = {}
projects: dict[str, dict] = {}
entries: dict[str, dict] = {}


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_profile(username: str, password_hash: str, content: dict) -> dict:
    profile = {
        "id": _new_id(),
        "username": username,
        "password_hash": password_hash,
        "content": content,
    }
    profiles[profile["id"]] = profile
    return profile


def get_profile(profile_id: str) -> dict | None:
    return profiles.get(profile_id)


def find_profile_by_username(username: str) -> dict | None:
    for profile in profiles.values():
        if profile["username"] == username:
            return profile
    return None


def public_profile(profile: dict) -> dict:
    """Profile without password_hash — the only shape safe to send to a client."""
    return {k: v for k, v in profile.items() if k != "password_hash"}


def create_project(name: str, creator_id: str) -> dict:
    project = {
        "id": _new_id(),
        "name": name,
        "ir": [],
        "users": [creator_id],
        "admins": [creator_id],
    }
    projects[project["id"]] = project
    return project


def get_project(project_id: str) -> dict | None:
    return projects.get(project_id)


def projects_for_user(user_id: str) -> list[dict]:
    return [p for p in projects.values() if user_id in p["users"]]


def projects_without_user(user_id: str) -> list[dict]:
    return [p for p in projects.values() if user_id not in p["users"]]


def create_entry(content: dict, author: str) -> dict:
    entry = {"id": _new_id(), "content": content, "author": author, "created_at": _now()}
    entries[entry["id"]] = entry
    return entry


def add_entry_to_project(project_id: str, entry_id: str) -> None:
    projects[project_id]["ir"].append(entry_id)


def add_member(project_id: str, user_id: str) -> None:
    users = projects[project_id]["users"]
    if user_id not in users:
        users.append(user_id)
