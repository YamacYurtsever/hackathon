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


def promote_admin(project_id: str, user_id: str) -> None:
    admins = projects[project_id]["admins"]
    if user_id not in admins:
        admins.append(user_id)


def remove_member(project_id: str, user_id: str) -> dict | None:
    """Remove a user from a project, keeping the invariant that a project with
    members always has at least one admin. Returns the updated project, or None
    if that was the last member and the project was deleted."""
    project = projects[project_id]

    if user_id in project["users"]:
        project["users"].remove(user_id)
    if user_id in project["admins"]:
        project["admins"].remove(user_id)

    # An empty project can never regain an admin — anyone joining later would
    # get plain membership — so drop it rather than leave it orphaned.
    if not project["users"]:
        del projects[project_id]
        return None

    # Last admin left but members remain: promote the longest-standing one.
    if not project["admins"]:
        project["admins"].append(project["users"][0])

    return project
