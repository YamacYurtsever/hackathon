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


class JsonStore:
    def __init__(self, data_dir: Path, schema_dir: Path) -> None:
        self.data_dir = data_dir
        self.projects_dir = data_dir / "projects"
        self.entries_dir = data_dir / "entries"
        self.documents_dir = data_dir / "documents"
        self._lock = threading.RLock()
        for directory in (
            self.projects_dir,
            self.entries_dir,
            self.documents_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

        self._project_validator = Draft7Validator(
            self._read_json(schema_dir / "project.schema.json")
        )
        self._entry_validator = Draft7Validator(
            self._read_json(schema_dir / "ir_entry.schema.json")
        )

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
    ) -> dict[str, Any]:
        project_id = f"prj_{uuid.uuid4().hex[:12]}"
        created_at = datetime.now(UTC).isoformat()
        entries = [
            {
                "id": f"ir_{uuid.uuid4().hex[:12]}",
                "content": fact,
                "author": "system:mistral",
                "created_at": created_at,
            }
            for fact in facts
        ]
        project = {
            "id": project_id,
            "name": Path(filename).stem,
            "ir": [entry["id"] for entry in entries],
            "users": [],
        }
        document = {
            "id": project_id,
            "filename": filename,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "page_count": len(pages),
            "created_at": created_at,
            "models": {
                "ocr": ocr_model,
                "ir": chat_model,
            },
            "pages": pages,
        }

        self._project_validator.validate(project)
        for entry in entries:
            self._entry_validator.validate(entry)

        with self._lock:
            for entry in entries:
                self._write_json(
                    self.entries_dir / f"{entry['id']}.json",
                    entry,
                )
            self._write_json(
                self.projects_dir / f"{project_id}.json",
                project,
            )
            self._write_json(
                self.documents_dir / f"{project_id}.json",
                document,
            )
        return self._public_bundle(project, document, entries)

    def list_documents(self) -> list[dict[str, Any]]:
        documents = []
        with self._lock:
            for path in self.documents_dir.glob("prj_*.json"):
                document = self._read_json(path)
                project_path = self.projects_dir / f"{document['id']}.json"
                if not project_path.exists():
                    continue
                project = self._read_json(project_path)
                documents.append(
                    {
                        **self._public_document(document),
                        "name": project["name"],
                        "entry_count": len(project["ir"]),
                    }
                )
        return sorted(
            documents,
            key=lambda item: item["created_at"],
            reverse=True,
        )

    def get_bundle(self, project_id: str) -> dict[str, Any]:
        self._validate_identifier(project_id, "prj_")
        project_path = self.projects_dir / f"{project_id}.json"
        document_path = self.documents_dir / f"{project_id}.json"
        with self._lock:
            if not project_path.exists() or not document_path.exists():
                raise RecordNotFoundError(project_id)
            project = self._read_json(project_path)
            document = self._read_json(document_path)
            entries = []
            for entry_id in project["ir"]:
                self._validate_identifier(entry_id, "ir_")
                entry_path = self.entries_dir / f"{entry_id}.json"
                if entry_path.exists():
                    entries.append(self._read_json(entry_path))
        return self._public_bundle(project, document, entries)

    @staticmethod
    def _public_bundle(
        project: dict[str, Any],
        document: dict[str, Any],
        entries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "project": project,
            "document": JsonStore._public_document(document),
            "entries": entries,
        }

    @staticmethod
    def _public_document(document: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in document.items()
            if key != "pages"
        }

    @staticmethod
    def _validate_identifier(identifier: str, prefix: str) -> None:
        if (
            not identifier.startswith(prefix)
            or len(identifier) > 64
            or not identifier.replace("_", "").isalnum()
        ):
            raise RecordNotFoundError(identifier)

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
