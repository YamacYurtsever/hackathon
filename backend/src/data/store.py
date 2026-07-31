"""Storage. SQLite via stdlib `sqlite3` — file-based, no server, survives restart.

Every read assembles plain dicts in the same shape the rest of the app already
expects, so blueprints don't know or care that this stopped being in-memory.
The one thing persistence changes: a returned dict is a *copy*, so mutating it
no longer writes anything. Changes go through a function or they don't happen.
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone

# backend/data.db — anchored to the backend root, not to this file's package, so
# moving this module doesn't quietly relocate everyone's database.
_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_PATH = os.path.join(_BACKEND_ROOT, "data.db")

_path = DEFAULT_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    id            TEXT PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    content       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id   TEXT PRIMARY KEY,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entries (
    id         TEXT PRIMARY KEY,
    content    TEXT NOT NULL,
    author     TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- seq gives a stable insertion order, which both lists depend on: the feed
-- reads chronologically, and auto-promotion picks the longest-standing member.
CREATE TABLE IF NOT EXISTS project_users (
    seq        INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id    TEXT NOT NULL,
    is_admin   INTEGER NOT NULL DEFAULT 0,
    UNIQUE(project_id, user_id)
);

CREATE TABLE IF NOT EXISTS project_entries (
    seq        INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    entry_id   TEXT NOT NULL REFERENCES entries(id),
    UNIQUE(project_id, entry_id)
);

-- One proposed change waiting on an admin. A message that proposes three things
-- makes three requests, so each can be accepted or rejected on its own.
CREATE TABLE IF NOT EXISTS requests (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    author      TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    source_text TEXT NOT NULL,
    operation   TEXT NOT NULL
);

-- Two entries in the same project that can't both be true. Not a proposal and
-- not a fact: a state the record is in until someone settles it.
--
-- Dismissed rows are kept rather than deleted. "These don't actually conflict"
-- is a decision, and without a record of it the next merge re-detects the same
-- pair and the badge never goes away.
CREATE TABLE IF NOT EXISTS conflicts (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    entry_a     TEXT NOT NULL REFERENCES entries(id),
    entry_b     TEXT NOT NULL REFERENCES entries(id),
    reason      TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    dismissed   INTEGER NOT NULL DEFAULT 0,
    -- The pair, ordered, so the same two entries can't be recorded twice.
    UNIQUE(project_id, entry_a, entry_b)
);
"""


def init_db(path: str | None = None) -> None:
    """Point the store at a database file and create the schema if needed."""
    global _path
    if path is not None:
        _path = path
    with _connect() as conn:
        conn.executescript(SCHEMA)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_path)
    conn.row_factory = sqlite3.Row
    # Off by default in sqlite, and we rely on it to cascade a deleted project's
    # membership and entry links away.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- profiles ---


def _profile_from_row(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "username": row["username"],
        "password_hash": row["password_hash"],
        "content": json.loads(row["content"]),
    }


def create_profile(username: str, password_hash: str, content: dict) -> dict:
    profile = {
        "id": _new_id(),
        "username": username,
        "password_hash": password_hash,
        "content": content,
    }
    with _connect() as conn:
        conn.execute(
            "INSERT INTO profiles (id, username, password_hash, content) VALUES (?, ?, ?, ?)",
            (profile["id"], username, password_hash, json.dumps(content)),
        )
    return profile


def get_profile(profile_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    return _profile_from_row(row) if row else None


def find_profile_by_username(username: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM profiles WHERE username = ?", (username,)
        ).fetchone()
    return _profile_from_row(row) if row else None


def update_profile_content(profile_id: str, content: dict) -> dict | None:
    """Replaces a profile's self-description. Needed because the returned dict is
    a copy — assigning to it no longer persists anything."""
    with _connect() as conn:
        conn.execute(
            "UPDATE profiles SET content = ? WHERE id = ?",
            (json.dumps(content), profile_id),
        )
    return get_profile(profile_id)


def public_profile(profile: dict) -> dict:
    """Profile without password_hash — the only shape safe to send to a client."""
    return {k: v for k, v in profile.items() if k != "password_hash"}


# --- projects ---


def _project_from_row(conn: sqlite3.Connection, row: sqlite3.Row) -> dict:
    members = conn.execute(
        "SELECT user_id, is_admin FROM project_users WHERE project_id = ? ORDER BY seq",
        (row["id"],),
    ).fetchall()
    entry_ids = conn.execute(
        "SELECT entry_id FROM project_entries WHERE project_id = ? ORDER BY seq",
        (row["id"],),
    ).fetchall()

    return {
        "id": row["id"],
        "name": row["name"],
        "ir": [entry["entry_id"] for entry in entry_ids],
        "users": [member["user_id"] for member in members],
        "admins": [member["user_id"] for member in members if member["is_admin"]],
    }


def create_project(name: str, creator_id: str) -> dict:
    project_id = _new_id()
    with _connect() as conn:
        conn.execute("INSERT INTO projects (id, name) VALUES (?, ?)", (project_id, name))
        conn.execute(
            "INSERT INTO project_users (project_id, user_id, is_admin) VALUES (?, ?, 1)",
            (project_id, creator_id),
        )
    return {
        "id": project_id,
        "name": name,
        "ir": [],
        "users": [creator_id],
        "admins": [creator_id],
    }


def get_project(project_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
        return _project_from_row(conn, row) if row else None


def projects_for_user(user_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """SELECT projects.* FROM projects
               JOIN project_users ON project_users.project_id = projects.id
               WHERE project_users.user_id = ?
               ORDER BY project_users.seq""",
            (user_id,),
        ).fetchall()
        return [_project_from_row(conn, row) for row in rows]


def add_member(project_id: str, user_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO project_users (project_id, user_id, is_admin) VALUES (?, ?, 0)",
            (project_id, user_id),
        )


def promote_admin(project_id: str, user_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE project_users SET is_admin = 1 WHERE project_id = ? AND user_id = ?",
            (project_id, user_id),
        )


def remove_member(project_id: str, user_id: str) -> dict | None:
    """Remove a user from a project, keeping the invariant that a project with
    members always has at least one admin. Returns the updated project, or None
    if that was the last member and the project was deleted."""
    with _connect() as conn:
        conn.execute(
            "DELETE FROM project_users WHERE project_id = ? AND user_id = ?",
            (project_id, user_id),
        )

        remaining = conn.execute(
            "SELECT user_id, is_admin FROM project_users WHERE project_id = ? ORDER BY seq",
            (project_id,),
        ).fetchall()

        # An empty project can never regain an admin — anyone joining later would
        # get plain membership — so drop it rather than leave it orphaned.
        if not remaining:
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            return None

        # Last admin left but members remain: promote the longest-standing one.
        if not any(member["is_admin"] for member in remaining):
            conn.execute(
                "UPDATE project_users SET is_admin = 1 WHERE project_id = ? AND user_id = ?",
                (project_id, remaining[0]["user_id"]),
            )

    return get_project(project_id)


# --- IR entries ---


def create_entry(content: dict, author: str) -> dict:
    entry = {
        "id": _new_id(),
        "content": content,
        "author": author,
        "created_at": _now(),
    }
    with _connect() as conn:
        conn.execute(
            "INSERT INTO entries (id, content, author, created_at) VALUES (?, ?, ?, ?)",
            (entry["id"], json.dumps(content), author, entry["created_at"]),
        )
    return entry


def get_entry(entry_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "content": json.loads(row["content"]),
        "author": row["author"],
        "created_at": row["created_at"],
    }


def add_entry_to_project(project_id: str, entry_id: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO project_entries (project_id, entry_id) VALUES (?, ?)",
            (project_id, entry_id),
        )


def entries_for_project(project_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            """SELECT entries.* FROM entries
               JOIN project_entries ON project_entries.entry_id = entries.id
               WHERE project_entries.project_id = ?
               ORDER BY project_entries.seq""",
            (project_id,),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "content": json.loads(row["content"]),
            "author": row["author"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


# --- requests (confirmed changesets awaiting an admin) ---


def _request_from_row(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "author": row["author"],
        "created_at": row["created_at"],
        "source_text": row["source_text"],
        "operation": json.loads(row["operation"]),
    }


def create_request(
    project_id: str, author: str, source_text: str, operation: dict
) -> dict:
    request = {
        "id": _new_id(),
        "project_id": project_id,
        "author": author,
        "created_at": _now(),
        "source_text": source_text,
        "operation": operation,
    }
    with _connect() as conn:
        conn.execute(
            """INSERT INTO requests (id, project_id, author, created_at, source_text, operation)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                request["id"],
                project_id,
                author,
                request["created_at"],
                source_text,
                json.dumps(operation),
            ),
        )
    return request


def get_request(request_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
    return _request_from_row(row) if row else None


def requests_for_project(project_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM requests WHERE project_id = ? ORDER BY created_at",
            (project_id,),
        ).fetchall()
    return [_request_from_row(row) for row in rows]


def update_request_operation(request_id: str, operation: dict) -> dict | None:
    with _connect() as conn:
        conn.execute(
            "UPDATE requests SET operation = ? WHERE id = ?",
            (json.dumps(operation), request_id),
        )
    return get_request(request_id)


def delete_request(request_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM requests WHERE id = ?", (request_id,))


def merge_request(request_id: str) -> tuple[str | None, str | None]:
    """Merges a request's operation into the IR, then deletes the request.

    Returns the affected entry id, or an error message with nothing written —
    an update naming an entry that has since vanished is refused rather than
    silently landing as a create.

    This is the only function that writes to the IR.
    """
    request = get_request(request_id)
    if request is None:
        return None, "request not found"

    operation = request["operation"]
    with _connect() as conn:
        if operation.get("op") == "update":
            target_id = operation.get("target_id")
            present = conn.execute(
                "SELECT 1 FROM project_entries WHERE project_id = ? AND entry_id = ?",
                (request["project_id"], target_id),
            ).fetchone()
            if present is None:
                conn.rollback()
                return None, f"entry {target_id} is no longer in this project"

            conn.execute(
                "UPDATE entries SET content = ?, author = ?, created_at = ? WHERE id = ?",
                (
                    json.dumps(operation["content"]),
                    # The proposer, not whichever admin merged or edited it.
                    request["author"],
                    _now(),
                    target_id,
                ),
            )
            entry_id = target_id
        else:
            entry_id = _new_id()
            conn.execute(
                "INSERT INTO entries (id, content, author, created_at) VALUES (?, ?, ?, ?)",
                (entry_id, json.dumps(operation["content"]), request["author"], _now()),
            )
            conn.execute(
                "INSERT INTO project_entries (project_id, entry_id) VALUES (?, ?)",
                (request["project_id"], entry_id),
            )

        conn.execute("DELETE FROM requests WHERE id = ?", (request_id,))

    return entry_id, None


# --- conflicts ---
#
# A conflict is between two entries that are both already in the IR. It isn't a
# proposal, so it never queues; it's a state the project is in until an admin
# edits one side, discards one, or says the two don't actually contradict.


def _conflict_from_row(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "entry_ids": [row["entry_a"], row["entry_b"]],
        "reason": row["reason"],
        "created_at": row["created_at"],
        "dismissed": bool(row["dismissed"]),
    }


def _pair(entry_a: str, entry_b: str) -> tuple[str, str]:
    """Ordered, so (a, b) and (b, a) are the same pair to the UNIQUE index."""
    return (entry_a, entry_b) if entry_a <= entry_b else (entry_b, entry_a)


def record_conflict(project_id: str, entry_a: str, entry_b: str, reason: str) -> dict | None:
    """Records a contradiction, or returns None if this pair is already known.

    Already known includes dismissed: someone has ruled on these two, and
    re-raising it on the next merge would make that ruling meaningless.
    """
    first, second = _pair(entry_a, entry_b)
    conflict = {
        "id": _new_id(),
        "project_id": project_id,
        "entry_ids": [first, second],
        "reason": reason,
        "created_at": _now(),
        "dismissed": False,
    }
    with _connect() as conn:
        existing = conn.execute(
            "SELECT 1 FROM conflicts WHERE project_id = ? AND entry_a = ? AND entry_b = ?",
            (project_id, first, second),
        ).fetchone()
        if existing is not None:
            return None
        conn.execute(
            "INSERT INTO conflicts (id, project_id, entry_a, entry_b, reason, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (conflict["id"], project_id, first, second, reason, conflict["created_at"]),
        )
    return conflict


def conflicts_for_project(project_id: str) -> list[dict]:
    """Open conflicts, oldest first. Dismissed ones stay in the table but are
    settled, so they aren't anybody's problem any more."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM conflicts WHERE project_id = ? AND dismissed = 0"
            " ORDER BY created_at",
            (project_id,),
        ).fetchall()
    return [_conflict_from_row(row) for row in rows]


def get_conflict(conflict_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM conflicts WHERE id = ?", (conflict_id,)
        ).fetchone()
    return _conflict_from_row(row) if row else None


def dismiss_conflict(conflict_id: str) -> None:
    with _connect() as conn:
        conn.execute("UPDATE conflicts SET dismissed = 1 WHERE id = ?", (conflict_id,))


def resolve_conflict(conflict_id: str) -> None:
    """Gone for good: the contradiction it named no longer exists, so unlike a
    dismissal there's nothing to remember."""
    with _connect() as conn:
        conn.execute("DELETE FROM conflicts WHERE id = ?", (conflict_id,))


def update_entry_content(entry_id: str, content: dict) -> dict | None:
    """Edits an entry already in the IR.

    Authorship doesn't move: the fact is still the proposer's, and an admin
    fixing a contradiction is not claiming it. `created_at` does move, because
    the digest and the summary cache both key off it and this is a change.
    """
    with _connect() as conn:
        changed = conn.execute(
            "UPDATE entries SET content = ?, created_at = ? WHERE id = ?",
            (json.dumps(content), _now(), entry_id),
        ).rowcount
    return get_entry(entry_id) if changed else None


def remove_entry(project_id: str, entry_id: str) -> None:
    """Drops a fact from a project, and with it any conflict that named it.

    The only place the IR loses a fact — the entry row itself is left alone, so
    nothing else that referenced it breaks.
    """
    with _connect() as conn:
        conn.execute(
            "DELETE FROM project_entries WHERE project_id = ? AND entry_id = ?",
            (project_id, entry_id),
        )
        conn.execute(
            "DELETE FROM conflicts WHERE project_id = ? AND (entry_a = ? OR entry_b = ?)",
            (project_id, entry_id, entry_id),
        )
