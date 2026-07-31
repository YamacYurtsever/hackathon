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
        self.issues_dir = data_dir / "issues"
        self.versions_dir = data_dir / "versions"
        self._lock = threading.RLock()
        for directory in (
            self.projects_dir,
            self.entries_dir,
            self.profiles_dir,
            self.documents_dir,
            self.issues_dir,
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
        self._issue_validator = Draft7Validator(
            self._read_json(schema_dir / "issue.schema.json")
        )

    def create_profile(
        self,
        content: dict[str, Any],
        *,
        profile_id: str | None = None,
        username: str | None = None,
        password_hash: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(content, dict):
            raise ValueError("Profile content must be an object.")
        profile = {
            "id": profile_id or f"user_{uuid.uuid4().hex[:12]}",
            "content": content,
        }
        if username is not None:
            normalized_username = username.strip()
            if not normalized_username:
                raise ValueError("Username is required.")
            profile["username"] = normalized_username
        if password_hash is not None:
            profile["password_hash"] = password_hash
        self._validate_identifier(profile["id"], "user_")
        self._profile_validator.validate(profile)
        path = self.profiles_dir / f"{profile['id']}.json"
        with self._lock:
            if username is not None and self.find_profile_by_username(username):
                raise StoreConflictError("That username is already taken.")
            if path.exists():
                raise StoreConflictError("A profile with that ID already exists.")
            self._write_json(path, profile)
        return self._public_profile(profile)

    def update_profile_account(
        self,
        profile_id: str,
        *,
        username: str,
        password_hash: str,
    ) -> dict[str, Any]:
        """Add or refresh login fields while preserving a profile's context."""
        normalized_username = username.strip()
        if not normalized_username:
            raise ValueError("Username is required.")
        with self._lock:
            profile = self._get_profile_record(profile_id)
            existing = self.find_profile_by_username(normalized_username)
            if existing and existing["id"] != profile_id:
                raise StoreConflictError("That username is already taken.")
            profile["username"] = normalized_username
            profile["password_hash"] = password_hash
            self._profile_validator.validate(profile)
            self._write_json(
                self.profiles_dir / f"{profile_id}.json",
                profile,
            )
        return self._public_profile(profile)

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
        return self._public_profile(self._get_profile_record(profile_id))

    def get_profile_for_auth(self, profile_id: str) -> dict[str, Any]:
        return self._get_profile_record(profile_id)

    def find_profile_by_username(
        self,
        username: str,
    ) -> dict[str, Any] | None:
        normalized_username = username.strip().casefold()
        if not normalized_username:
            return None
        with self._lock:
            for path in self.profiles_dir.glob("user_*.json"):
                profile = self._read_json(path)
                stored_username = profile.get("username")
                if (
                    isinstance(stored_username, str)
                    and stored_username.casefold() == normalized_username
                ):
                    return profile
        return None

    def update_profile_content(
        self,
        profile_id: str,
        content: dict[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(content, dict):
            raise ValueError("Profile content must be an object.")
        with self._lock:
            profile = self._get_profile_record(profile_id)
            profile["content"] = content
            self._profile_validator.validate(profile)
            self._write_json(
                self.profiles_dir / f"{profile_id}.json",
                profile,
            )
        return self._public_profile(profile)

    def _get_profile_record(self, profile_id: str) -> dict[str, Any]:
        self._validate_identifier(profile_id, "user_")
        path = self.profiles_dir / f"{profile_id}.json"
        with self._lock:
            if not path.exists():
                raise RecordNotFoundError(profile_id)
            return self._read_json(path)

    def list_profiles(self) -> list[dict[str, Any]]:
        with self._lock:
            profiles = [
                self._public_profile(self._read_json(path))
                for path in self.profiles_dir.glob("user_*.json")
            ]
        return sorted(
            profiles,
            key=lambda profile: str(
                profile.get("content", {}).get("name")
                or profile.get("username")
                or profile["id"]
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
            "documents": [],
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
        return self.add_document(
            project["id"],
            filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            pages=pages,
            facts=facts,
            ocr_model=ocr_model,
            chat_model=chat_model,
            author_id=author_id,
        )

    def add_document(
        self,
        project_id: str,
        *,
        filename: str,
        mime_type: str,
        size_bytes: int,
        pages: list[dict[str, Any]],
        facts: list[dict[str, Any]],
        ocr_model: str,
        chat_model: str,
        author_id: str,
    ) -> dict[str, Any]:
        project = self.get_project(project_id)
        if author_id not in project["users"]:
            raise PermissionDeniedError(
                "Only project members can add documents."
            )
        document_id = f"doc_{uuid.uuid4().hex[:12]}"
        grounded_facts = []
        for fact in facts:
            fact_copy = {**fact}
            source = fact.get("source")
            if isinstance(source, dict):
                fact_copy["source"] = {
                    **source,
                    "document_id": document_id,
                    "filename": filename,
                }
            grounded_facts.append(fact_copy)

        entries = self.append_entries(
            project_id,
            grounded_facts,
            author_id,
        )
        document = {
            "id": document_id,
            "project_id": project_id,
            "filename": filename,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "page_count": len(pages),
            "created_at": self._now(),
            "author": author_id,
            "models": {
                "ocr": ocr_model,
                "ir": chat_model,
            },
            "pages": pages,
        }
        with self._lock:
            project = self.get_project(project_id)
            self._write_json(
                self.documents_dir / f"{document_id}.json",
                document,
            )
            project["documents"].append(document_id)
            self._project_validator.validate(project)
            self._write_json(
                self.projects_dir / f"{project_id}.json",
                project,
            )
        return self.get_bundle(project_id)

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
            if "documents" not in project:
                legacy_document_path = self.documents_dir / f"{project_id}.json"
                project["documents"] = (
                    [project_id] if legacy_document_path.exists() else []
                )
                changed = True
            if changed:
                self._write_json(path, project)
            return project

    def list_projects(
        self,
        member_id: str | None = None,
    ) -> list[dict[str, Any]]:
        projects = []
        with self._lock:
            paths = list(self.projects_dir.glob("prj_*.json"))
        for path in paths:
            project = self.get_project(path.stem)
            if member_id is not None and member_id not in project["users"]:
                continue
            documents = self._get_documents(project)
            document = documents[-1] if documents else None
            projects.append(
                {
                    "id": project["id"],
                    "name": project["name"],
                    "entry_count": len(project["ir"]),
                    "member_count": len(project["users"]),
                    "document_count": len(documents),
                    "created_at": project["created_at"],
                    "document": (
                        self._public_document(document)
                        if document is not None
                        else None
                    ),
                }
            )
        return sorted(
            projects,
            key=lambda item: item["created_at"],
            reverse=True,
        )

    def list_documents(
        self,
        member_id: str | None = None,
    ) -> list[dict[str, Any]]:
        documents = []
        for summary in self.list_projects(member_id):
            project = self.get_project(summary["id"])
            documents.extend(
                {
                    **self._public_document(document),
                    "name": project["name"],
                    "entry_count": summary["entry_count"],
                }
                for document in self._get_documents(project)
            )
        return sorted(
            documents,
            key=lambda document: document["created_at"],
            reverse=True,
        )

    def get_bundle(self, project_id: str) -> dict[str, Any]:
        project = self.get_project(project_id)
        with self._lock:
            documents = self._get_documents(project)
            entries = []
            for entry_id in project["ir"]:
                self._validate_identifier(entry_id, "ir_")
                entry_path = self.entries_dir / f"{entry_id}.json"
                if entry_path.exists():
                    entries.append(self._read_json(entry_path))
        return self._public_bundle(project, documents, entries)

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

    def add_member(
        self,
        project_id: str,
        caller_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        self.get_profile(user_id)
        with self._lock:
            project = self.get_project(project_id)
            if caller_id not in project["admins"]:
                raise PermissionDeniedError(
                    "Only a project admin can add members."
                )
            if user_id not in project["users"]:
                project["users"].append(user_id)
                self._project_validator.validate(project)
                self._write_json(
                    self.projects_dir / f"{project_id}.json",
                    project,
                )
        return project

    def remove_member(
        self,
        project_id: str,
        caller_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        with self._lock:
            project = self.get_project(project_id)
            if caller_id not in project["admins"]:
                raise PermissionDeniedError(
                    "Only a project admin can remove members."
                )
            if caller_id == user_id:
                raise ValueError(
                    "Use the exit-project action to remove yourself."
                )
            if user_id not in project["users"]:
                raise ValueError("The user is not a project member.")
            assigned_open_issue = next(
                (
                    issue
                    for issue in self.list_issues(project_id, caller_id)
                    if issue["status"] == "open"
                    and user_id in issue["reviewer_ids"]
                ),
                None,
            )
            if assigned_open_issue is not None:
                raise StoreConflictError(
                    "Resolve the member's assigned issue reviews before removing them."
                )
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

    def join_project(
        self,
        project_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        self.get_profile(user_id)
        with self._lock:
            project = self.get_project(project_id)
            if user_id not in project["users"]:
                project["users"].append(user_id)
                self._project_validator.validate(project)
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
            assigned_open_issue = next(
                (
                    issue
                    for issue in self.list_issues(project_id, user_id)
                    if issue["status"] == "open"
                    and user_id in issue["reviewer_ids"]
                ),
                None,
            )
            if assigned_open_issue is not None:
                raise StoreConflictError(
                    "Complete assigned issue reviews before exiting the project."
                )
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

    def create_issue(
        self,
        project_id: str,
        *,
        title: str,
        summary: str,
        required_expertise: str,
        reviewer_ids: list[str],
        creator_id: str,
    ) -> dict[str, Any]:
        project = self.get_project(project_id)
        if creator_id not in project["users"]:
            raise PermissionDeniedError(
                "Only project members can create issues."
            )
        reviewers = list(dict.fromkeys(reviewer_ids))
        if not reviewers:
            raise ValueError("Select at least one expert reviewer.")
        if creator_id in reviewers:
            raise ValueError(
                "The issue creator cannot be their own expert reviewer."
            )
        if any(reviewer_id not in project["users"] for reviewer_id in reviewers):
            raise ValueError("Every reviewer must be a project member.")
        issue = {
            "id": f"iss_{uuid.uuid4().hex[:12]}",
            "project_id": project_id,
            "title": title.strip(),
            "summary": summary.strip(),
            "required_expertise": required_expertise.strip(),
            "reviewer_ids": reviewers,
            "status": "open",
            "created_by": creator_id,
            "created_at": self._now(),
            "proposals": [],
        }
        self._issue_validator.validate(issue)
        with self._lock:
            self._write_json(
                self.issues_dir / f"{issue['id']}.json",
                issue,
            )
        return issue

    def list_issues(
        self,
        project_id: str,
        viewer_id: str,
    ) -> list[dict[str, Any]]:
        project = self.get_project(project_id)
        if viewer_id not in project["users"]:
            raise PermissionDeniedError(
                "Only project members can view issues."
            )
        with self._lock:
            issues = [
                self._read_json(path)
                for path in self.issues_dir.glob("iss_*.json")
            ]
        return sorted(
            (
                issue
                for issue in issues
                if issue.get("project_id") == project_id
            ),
            key=lambda issue: (
                issue.get("status") == "open",
                issue["created_at"],
            ),
            reverse=True,
        )

    def create_proposal(
        self,
        project_id: str,
        issue_id: str,
        solution: str,
        author_id: str,
    ) -> dict[str, Any]:
        with self._lock:
            issue = self._get_issue(project_id, issue_id)
            self._require_open_issue(issue)
            self._require_issue_contributor(issue, author_id)
            proposal = {
                "id": f"prop_{uuid.uuid4().hex[:12]}",
                "status": "draft",
                "contributors": [author_id],
                "created_at": self._now(),
                "versions": [
                    {
                        "version": 1,
                        "solution": solution.strip(),
                        "author": author_id,
                        "created_at": self._now(),
                    }
                ],
                "reviews": [],
            }
            issue["proposals"].append(proposal)
            self._write_issue(issue)
        return issue

    def revise_proposal(
        self,
        project_id: str,
        issue_id: str,
        proposal_id: str,
        solution: str,
        base_version: int,
        author_id: str,
    ) -> dict[str, Any]:
        with self._lock:
            issue = self._get_issue(project_id, issue_id)
            self._require_open_issue(issue)
            self._require_issue_contributor(issue, author_id)
            proposal = self._get_proposal(issue, proposal_id)
            if proposal["status"] not in {"draft", "rejected"}:
                raise ValueError(
                    "A submitted proposal must be reviewed before it can change."
                )
            current_version = proposal["versions"][-1]["version"]
            if base_version != current_version:
                raise StoreConflictError(
                    "This solution branch advanced. Reload before adding your revision."
                )
            if author_id not in proposal["contributors"]:
                proposal["contributors"].append(author_id)
            proposal["versions"].append(
                {
                    "version": len(proposal["versions"]) + 1,
                    "solution": solution.strip(),
                    "author": author_id,
                    "created_at": self._now(),
                }
            )
            proposal["status"] = "draft"
            self._write_issue(issue)
        return issue

    def submit_proposal(
        self,
        project_id: str,
        issue_id: str,
        proposal_id: str,
        author_id: str,
    ) -> dict[str, Any]:
        with self._lock:
            issue = self._get_issue(project_id, issue_id)
            self._require_open_issue(issue)
            self._require_current_issue_member(issue, author_id)
            proposal = self._get_proposal(issue, proposal_id)
            if author_id not in proposal["contributors"]:
                raise PermissionDeniedError(
                    "Only a proposal contributor can submit it for review."
                )
            if proposal["status"] != "draft":
                raise ValueError("Only a draft proposal can be submitted.")
            proposal["status"] = "in_review"
            self._write_issue(issue)
        return issue

    def review_proposal(
        self,
        project_id: str,
        issue_id: str,
        proposal_id: str,
        *,
        reviewer_id: str,
        decision: str,
        comment: str,
    ) -> dict[str, Any]:
        with self._lock:
            issue = self._get_issue(project_id, issue_id)
            self._require_open_issue(issue)
            self._require_current_issue_member(issue, reviewer_id)
            proposal = self._get_proposal(issue, proposal_id)
            if reviewer_id not in issue["reviewer_ids"]:
                raise PermissionDeniedError(
                    "Only an assigned expert reviewer can review this proposal."
                )
            if reviewer_id in proposal["contributors"]:
                raise PermissionDeniedError(
                    "Proposal contributors cannot approve their own work."
                )
            if proposal["status"] != "in_review":
                raise ValueError("The proposal is not awaiting review.")
            if decision not in {"approved", "rejected"}:
                raise ValueError("Decision must be 'approved' or 'rejected'.")
            current_version = proposal["versions"][-1]
            proposal["reviews"].append(
                {
                    "reviewer": reviewer_id,
                    "decision": decision,
                    "comment": comment.strip(),
                    "version": current_version["version"],
                    "created_at": self._now(),
                }
            )
            proposal["status"] = decision
            if decision == "approved":
                entry = self.append_entries(
                    project_id,
                    [
                        {
                            "statement": current_version["solution"],
                            "category": "decision",
                            "entities": [issue["title"]],
                            "source": {
                                "kind": "issue",
                                "issue_id": issue_id,
                                "proposal_id": proposal_id,
                                "version": current_version["version"],
                                "quote": current_version["solution"][:500],
                            },
                            "confidence": "high",
                        }
                    ],
                    reviewer_id,
                )[0]
                issue["status"] = "resolved"
                issue["resolved_at"] = self._now()
                issue["approved_proposal_id"] = proposal_id
                issue["resolution_entry_id"] = entry["id"]
            self._write_issue(issue)
        return issue

    def _get_issue(
        self,
        project_id: str,
        issue_id: str,
    ) -> dict[str, Any]:
        self._validate_identifier(issue_id, "iss_")
        path = self.issues_dir / f"{issue_id}.json"
        if not path.exists():
            raise RecordNotFoundError(issue_id)
        issue = self._read_json(path)
        if issue.get("project_id") != project_id:
            raise RecordNotFoundError(issue_id)
        return issue

    def _write_issue(self, issue: dict[str, Any]) -> None:
        self._issue_validator.validate(issue)
        self._write_json(
            self.issues_dir / f"{issue['id']}.json",
            issue,
        )

    @staticmethod
    def _get_proposal(
        issue: dict[str, Any],
        proposal_id: str,
    ) -> dict[str, Any]:
        for proposal in issue["proposals"]:
            if proposal["id"] == proposal_id:
                return proposal
        raise RecordNotFoundError(proposal_id)

    @staticmethod
    def _require_open_issue(issue: dict[str, Any]) -> None:
        if issue["status"] != "open":
            raise ValueError("This issue is already resolved.")

    def _require_issue_contributor(
        self,
        issue: dict[str, Any],
        user_id: str,
    ) -> None:
        self._require_current_issue_member(issue, user_id)
        if user_id in issue["reviewer_ids"]:
            raise PermissionDeniedError(
                "Assigned reviewers must remain independent from contributors."
            )

    def _require_current_issue_member(
        self,
        issue: dict[str, Any],
        user_id: str,
    ) -> None:
        project = self.get_project(issue["project_id"])
        if user_id not in project["users"]:
            raise PermissionDeniedError(
                "Only current project members can work on issues."
            )

    def get_versions(self, entry_id: str) -> list[dict[str, Any]]:
        self._validate_identifier(entry_id, "ir_")
        path = self.versions_dir / f"{entry_id}.json"
        with self._lock:
            if not path.exists():
                raise RecordNotFoundError(entry_id)
            value = self._read_json(path)
        return value.get("versions", [])

    def get_entry_project(self, entry_id: str) -> dict[str, Any]:
        self._validate_identifier(entry_id, "ir_")
        with self._lock:
            paths = list(self.projects_dir.glob("prj_*.json"))
        for path in paths:
            project = self.get_project(path.stem)
            if entry_id in project["ir"]:
                return project
        raise RecordNotFoundError(entry_id)

    @staticmethod
    def _public_bundle(
        project: dict[str, Any],
        documents: list[dict[str, Any]],
        entries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        public_documents = [
            JsonStore._public_document(document)
            for document in documents
        ]
        return {
            "project": project,
            "documents": public_documents,
            # Kept for older clients while the UI moves to document collections.
            "document": public_documents[-1] if public_documents else None,
            "entries": entries,
        }

    def _get_documents(
        self,
        project: dict[str, Any],
    ) -> list[dict[str, Any]]:
        documents = []
        for document_id in project.get("documents", []):
            if not isinstance(document_id, str):
                continue
            expected_prefix = (
                "prj_" if document_id == project["id"] else "doc_"
            )
            try:
                self._validate_identifier(document_id, expected_prefix)
            except RecordNotFoundError:
                continue
            document_path = self.documents_dir / f"{document_id}.json"
            if document_path.exists():
                documents.append(self._read_json(document_path))
        return documents

    @staticmethod
    def _public_document(document: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in document.items()
            if key != "pages"
        }

    @staticmethod
    def _public_profile(profile: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in profile.items()
            if key != "password_hash"
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
