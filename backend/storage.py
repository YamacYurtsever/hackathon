import json
import os
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator


class RecordNotFoundError(KeyError):
    pass


class PermissionDeniedError(RuntimeError):
    pass


class StoreConflictError(RuntimeError):
    pass


class JsonStore:
    SYSTEM_PROFILE_ID = "user_mistral"

    def __init__(self, data_dir: Path, schema_dir: Path) -> None:
        self.data_dir = data_dir
        self.projects_dir = data_dir / "projects"
        self.entries_dir = data_dir / "entries"
        self.profiles_dir = data_dir / "profiles"
        self.documents_dir = data_dir / "documents"
        self.versions_dir = data_dir / "versions"
        self._lock = threading.RLock()
        for directory in (
            self.projects_dir,
            self.entries_dir,
            self.profiles_dir,
            self.documents_dir,
            self.versions_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

        self._project_validator = Draft7Validator(
            self._read_json(schema_dir / "project.schema.json")
        )
        self._entry_validator = Draft7Validator(
            self._read_json(schema_dir / "ir_entry.schema.json")
        )
        self._profile_validator = Draft7Validator(
            self._read_json(schema_dir / "profile.schema.json")
        )

    def create_profile(
        self,
        content: dict[str, Any],
        *,
        profile_id: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(content, dict):
            raise ValueError("Profile content must be an object.")
        profile = {
            "id": profile_id or f"user_{uuid.uuid4().hex[:12]}",
            "content": content,
        }
        self._validate_identifier(profile["id"], "user_")
        self._profile_validator.validate(profile)
        path = self.profiles_dir / f"{profile['id']}.json"
        with self._lock:
            if path.exists():
                raise StoreConflictError("A profile with that ID already exists.")
            self._write_json(path, profile)
        return profile

    def ensure_system_profile(self) -> dict[str, Any]:
        path = self.profiles_dir / f"{self.SYSTEM_PROFILE_ID}.json"
        with self._lock:
            if path.exists():
                return self._read_json(path)
            return self.create_profile(
                {
                    "name": "Mistral document importer",
                    "expertise": "Document extraction and neutral IR structuring",
                    "system": True,
                },
                profile_id=self.SYSTEM_PROFILE_ID,
            )

    def get_profile(self, profile_id: str) -> dict[str, Any]:
        self._validate_identifier(profile_id, "user_")
        path = self.profiles_dir / f"{profile_id}.json"
        with self._lock:
            if not path.exists():
                raise RecordNotFoundError(profile_id)
            return self._read_json(path)

    def list_profiles(self) -> list[dict[str, Any]]:
        with self._lock:
            profiles = [
                self._read_json(path)
                for path in self.profiles_dir.glob("user_*.json")
            ]
        return sorted(
            profiles,
            key=lambda profile: str(
                profile.get("content", {}).get("name", profile["id"])
            ).casefold(),
        )

    def create_project(
        self,
        name: str,
        creator_id: str,
        *,
        project_id: str | None = None,
        member_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        self.get_profile(creator_id)
        users = list(dict.fromkeys([creator_id, *(member_ids or [])]))
        for user_id in users:
            self.get_profile(user_id)
        project = {
            "id": project_id or f"prj_{uuid.uuid4().hex[:12]}",
            "name": name.strip(),
            "ir": [],
            "users": users,
            "admins": [creator_id],
            "created_at": self._now(),
        }
        if not project["name"]:
            raise ValueError("Project name is required.")
        self._validate_identifier(project["id"], "prj_")
        self._project_validator.validate(project)
        path = self.projects_dir / f"{project['id']}.json"
        with self._lock:
            if path.exists():
                raise StoreConflictError("A project with that ID already exists.")
            self._write_json(path, project)
        return project

    def append_entries(
        self,
        project_id: str,
        facts: list[dict[str, Any]],
        author_id: str,
    ) -> list[dict[str, Any]]:
        project = self.get_project(project_id)
        if author_id not in project["users"]:
            raise PermissionDeniedError(
                "Only project members can add IR entries."
            )
        created_at = self._now()
        entries = [
            {
                "id": f"ir_{uuid.uuid4().hex[:12]}",
                "content": fact,
                "author": author_id,
                "created_at": created_at,
            }
            for fact in facts
        ]
        for entry in entries:
            self._entry_validator.validate(entry)

        with self._lock:
            project = self.get_project(project_id)
            for entry in entries:
                self._write_json(
                    self.entries_dir / f"{entry['id']}.json",
                    entry,
                )
                self._append_version(entry)
            project["ir"].extend(entry["id"] for entry in entries)
            self._project_validator.validate(project)
            self._write_json(
                self.projects_dir / f"{project_id}.json",
                project,
            )
        return entries

    def create_document(
        self,
        *,
        filename: str,
        mime_type: str,
        size_bytes: int,
        pages: list[dict[str, Any]],
        facts: list[dict[str, Any]],
        ocr_model: str,
        chat_model: str,
        creator_id: str | None = None,
    ) -> dict[str, Any]:
        author_id = creator_id or self.SYSTEM_PROFILE_ID
        if creator_id is None:
            self.ensure_system_profile()
        else:
            self.get_profile(creator_id)
        project = self.create_project(Path(filename).stem, author_id)
        entries = self.append_entries(project["id"], facts, author_id)
        project = self.get_project(project["id"])
        document = {
            "id": project["id"],
            "filename": filename,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "page_count": len(pages),
            "created_at": project["created_at"],
            "models": {
                "ocr": ocr_model,
                "ir": chat_model,
            },
            "pages": pages,
        }
        with self._lock:
            self._write_json(
                self.documents_dir / f"{project['id']}.json",
                document,
            )
        return self._public_bundle(project, document, entries)

    def get_project(self, project_id: str) -> dict[str, Any]:
        self._validate_identifier(project_id, "prj_")
        path = self.projects_dir / f"{project_id}.json"
        with self._lock:
            if not path.exists():
                raise RecordNotFoundError(project_id)
            project = self._read_json(path)
            changed = False
            if not project.get("users"):
                self.ensure_system_profile()
                project["users"] = [self.SYSTEM_PROFILE_ID]
                changed = True
            if project.get("users") and not project.get("admins"):
                project["admins"] = project.get("users", [])[:1]
                changed = True
            if "created_at" not in project:
                project["created_at"] = datetime.fromtimestamp(
                    path.stat().st_mtime,
                    UTC,
                ).isoformat()
                changed = True
            if changed:
                self._write_json(path, project)
            return project

    def list_projects(self) -> list[dict[str, Any]]:
        projects = []
        with self._lock:
            paths = list(self.projects_dir.glob("prj_*.json"))
        for path in paths:
            project = self.get_project(path.stem)
            document_path = self.documents_dir / f"{project['id']}.json"
            document = (
                self._public_document(self._read_json(document_path))
                if document_path.exists()
                else None
            )
            projects.append(
                {
                    "id": project["id"],
                    "name": project["name"],
                    "entry_count": len(project["ir"]),
                    "member_count": len(project["users"]),
                    "created_at": project["created_at"],
                    "document": document,
                }
            )
        return sorted(
            projects,
            key=lambda item: item["created_at"],
            reverse=True,
        )

    def list_documents(self) -> list[dict[str, Any]]:
        return [
            {
                **project["document"],
                "name": project["name"],
                "entry_count": project["entry_count"],
            }
            for project in self.list_projects()
            if project["document"] is not None
        ]

    def get_bundle(self, project_id: str) -> dict[str, Any]:
        project = self.get_project(project_id)
        document_path = self.documents_dir / f"{project_id}.json"
        with self._lock:
            document = (
                self._read_json(document_path) if document_path.exists() else None
            )
            entries = []
            for entry_id in project["ir"]:
                self._validate_identifier(entry_id, "ir_")
                entry_path = self.entries_dir / f"{entry_id}.json"
                if entry_path.exists():
                    entries.append(self._read_json(entry_path))
        return self._public_bundle(project, document, entries)

    def get_changes(
        self,
        project_id: str,
        since: str,
    ) -> list[dict[str, Any]]:
        try:
            since_time = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("'since' must be an ISO-8601 timestamp.") from exc
        if since_time.tzinfo is None:
            since_time = since_time.replace(tzinfo=UTC)
        return [
            entry
            for entry in self.get_bundle(project_id)["entries"]
            if datetime.fromisoformat(entry["created_at"]) > since_time
        ]

    def promote_member(
        self,
        project_id: str,
        caller_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        with self._lock:
            project = self.get_project(project_id)
            if caller_id not in project["admins"]:
                raise PermissionDeniedError(
                    "Only a project admin can promote another member."
                )
            if user_id not in project["users"]:
                raise ValueError("The user must be a project member first.")
            if user_id not in project["admins"]:
                project["admins"].append(user_id)
            self._write_json(
                self.projects_dir / f"{project_id}.json",
                project,
            )
        return project

    def exit_project(
        self,
        project_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        with self._lock:
            project = self.get_project(project_id)
            if user_id not in project["users"]:
                raise ValueError("The user is not a project member.")
            project["users"].remove(user_id)
            if user_id in project["admins"]:
                project["admins"].remove(user_id)
            if project["users"] and not project["admins"]:
                project["admins"].append(project["users"][0])
            self._project_validator.validate(project)
            self._write_json(
                self.projects_dir / f"{project_id}.json",
                project,
            )
        return project

    def get_versions(self, entry_id: str) -> list[dict[str, Any]]:
        self._validate_identifier(entry_id, "ir_")
        path = self.versions_dir / f"{entry_id}.json"
        with self._lock:
            if not path.exists():
                raise RecordNotFoundError(entry_id)
            value = self._read_json(path)
        return value.get("versions", [])

    @staticmethod
    def _public_bundle(
        project: dict[str, Any],
        document: dict[str, Any] | None,
        entries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "project": project,
            "document": (
                JsonStore._public_document(document)
                if document is not None
                else None
            ),
            "entries": entries,
        }

    @staticmethod
    def _public_document(document: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in document.items()
            if key != "pages"
        }

    def _append_version(self, entry: dict[str, Any]) -> None:
        path = self.versions_dir / f"{entry['id']}.json"
        history = self._read_json(path) if path.exists() else {"versions": []}
        history["versions"].append(
            {
                "entry_id": entry["id"],
                "content": entry["content"],
                "author": entry["author"],
                "created_at": entry["created_at"],
            }
        )
        self._write_json(path, history)

    @staticmethod
    def _validate_identifier(identifier: str, prefix: str) -> None:
        if (
            not isinstance(identifier, str)
            or not identifier.startswith(prefix)
            or len(identifier) > 64
            or not identifier.replace("_", "").isalnum()
        ):
            raise RecordNotFoundError(identifier)

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        with path.open(encoding="utf-8") as file:
            return json.load(file)

    @staticmethod
    def _write_json(path: Path, value: dict[str, Any]) -> None:
        temporary_path = path.with_suffix(f"{path.suffix}.tmp")
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(value, file, ensure_ascii=False, indent=2)
            file.write("\n")
        os.replace(temporary_path, path)
