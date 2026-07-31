import base64
import json
import re
from collections.abc import Iterable
from typing import Any

from ir_models import (
    ConflictBatch,
    ExtractionBatch,
    ExtractedFact,
    GroundedAnswerDraft,
    ReprojectionBatch,
    read_content_path,
)


class MistralConfigurationError(RuntimeError):
    pass


class MistralProcessingError(RuntimeError):
    pass


class MistralDocumentService:
    def __init__(
        self,
        api_key: str,
        *,
        ocr_model: str = "mistral-ocr-latest",
        chat_model: str = "mistral-small-latest",
        chunk_characters: int = 30_000,
        client: Any | None = None,
    ) -> None:
        self.api_key = api_key
        self.ocr_model = ocr_model
        self.chat_model = chat_model
        self.chunk_characters = chunk_characters
        self._client = client

    @property
    def configured(self) -> bool:
        return bool(self.api_key or self._client)

    def process_document(
        self,
        content: bytes,
        mime_type: str,
    ) -> dict[str, Any]:
        client = self._get_client()
        data_url = (
            f"data:{mime_type};base64,"
            f"{base64.b64encode(content).decode('ascii')}"
        )
        is_image = mime_type.startswith("image/")
        document_type = "image_url" if is_image else "document_url"
        document_key = "image_url" if is_image else "document_url"

        try:
            response = client.ocr.process(
                model=self.ocr_model,
                document={
                    "type": document_type,
                    document_key: data_url,
                },
                include_image_base64=False,
            )
        except Exception as exc:
            raise MistralProcessingError(
                self._api_error_message(exc, "read this file")
            ) from exc

        pages = self._read_pages(response)
        if not pages:
            raise MistralProcessingError(
                "Mistral did not find readable content in this file."
            )

        extracted: list[ExtractedFact] = []
        for page_chunk in self._page_chunks(pages):
            extracted.extend(self._extract_chunk(client, page_chunk))

        grounded = self._ground_facts(extracted, pages)
        if not grounded:
            raise MistralProcessingError(
                "The file was read, but no source-grounded IR entries could be "
                "generated."
            )

        return {
            "pages": pages,
            "facts": [fact.model_dump(mode="json") for fact in grounded],
            "ocr_model": self.ocr_model,
            "chat_model": self.chat_model,
        }

    def extract_message(
        self,
        message: str,
        author_profile: dict[str, Any],
    ) -> list[dict[str, Any]]:
        client = self._get_client()
        system_prompt = (
            "Convert a person's natural-language project update into a neutral "
            "Intermediate Representation. Create one atomic entry per independently "
            "useful fact. Preserve exact names, quantities, dates, requirements, "
            "decisions, actions, changes, risks, and constraints. The author's "
            "profile helps you understand their vocabulary but must not become a "
            "fact. Extract only what the message explicitly supports; do not add "
            "implications or outside knowledge. Every entry must use source kind "
            "'message', page null, and a short verbatim quote from the message."
        )
        payload = {
            "author_profile": author_profile,
            "message": message,
        }
        try:
            response = client.chat.parse(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(payload, ensure_ascii=False),
                    },
                ],
                response_format=ExtractionBatch,
                temperature=0,
                max_tokens=3000,
            )
            result = self._parsed_response(response, ExtractionBatch)
        except Exception as exc:
            raise MistralProcessingError(
                self._api_error_message(exc, "extract structured IR")
            ) from exc

        facts = self._ground_message_facts(result.entries, message)
        if not facts:
            raise MistralProcessingError(
                "Mistral returned no IR entries whose evidence could be verified "
                "against the message."
            )
        return [fact.model_dump(mode="json") for fact in facts]

    def reproject_entries(
        self,
        entries: list[dict[str, Any]],
        viewer_profile: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if not entries:
            return []
        client = self._get_client()
        selected_entries = entries[-100:]
        system_prompt = (
            "Re-project the supplied neutral IR for this specific viewer. Shape "
            "vocabulary, emphasis, and implications using only the viewer's "
            "free-form profile; do not assume a fixed role. Surface useful, "
            "non-obvious implications when the IR supports them, and mark those "
            "claims as implications. Every claim must cite an exact supplied "
            "entry_id and one or more existing paths such as 'content.statement', "
            "'content.entities', 'content.category', or 'content.source.quote'. "
            "Never invent an ID or path. Do not introduce a factual assertion that "
            "cannot be traced to those paths."
        )
        payload = {
            "viewer_profile": viewer_profile,
            "ir_entries": [
                {"id": entry["id"], "content": entry["content"]}
                for entry in selected_entries
            ],
        }
        try:
            response = client.chat.parse(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(payload, ensure_ascii=False),
                    },
                ],
                response_format=ReprojectionBatch,
                temperature=0,
                max_tokens=5000,
            )
            batch = self._parsed_response(response, ReprojectionBatch)
        except Exception as exc:
            raise MistralProcessingError(
                self._api_error_message(exc, "re-project this project")
            ) from exc

        entries_by_id = {entry["id"]: entry for entry in selected_entries}
        claims = []
        for index, draft in enumerate(batch.claims):
            entry = entries_by_id.get(draft.entry_id)
            if entry is None:
                continue
            grounding = []
            for path in dict.fromkeys(draft.grounding_paths):
                value = read_content_path(entry, path)
                if value is not None:
                    grounding.append(
                        {
                            "entry_id": entry["id"],
                            "path": path,
                            "value": value,
                        }
                    )
            if not grounding:
                continue
            claims.append(
                {
                    "id": f"claim_{entry['id']}_{index + 1}",
                    "text": draft.text,
                    "entry_id": entry["id"],
                    "grounding": grounding,
                    "is_implication": draft.is_implication,
                    "author": entry.get("author"),
                    "created_at": entry.get("created_at"),
                }
            )
        return claims

    def detect_conflicts(
        self,
        new_entries: list[dict[str, Any]],
        existing_entries: list[dict[str, Any]],
        members: list[dict[str, Any]],
        open_issues: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Find only direct, source-grounded conflicts introduced by a change."""
        if not new_entries or not existing_entries or len(members) < 2:
            return []

        client = self._get_client()
        change_text = json.dumps(
            [entry.get("content", {}) for entry in new_entries],
            ensure_ascii=False,
        )
        selected_existing = self._select_relevant_entries(
            change_text,
            existing_entries,
            limit=100,
        )
        supplied_entries = [*selected_existing, *new_entries]
        system_prompt = (
            "Review new project IR entries against the existing IR and return only "
            "high-confidence direct conflicts. A conflict is a contradiction about "
            "the same property and conditions, a change that violates an explicit "
            "requirement or constraint, or a change inconsistent with an accepted "
            "decision. A downstream impact, new risk, missing work, ambiguity, or "
            "different scope is not a conflict. Every conflict must cite exact "
            "supplied entry IDs, including at least one new entry and one existing "
            "entry. Do not duplicate an open issue with the same evidence. Assign "
            "participants who own or can implement the conflicting work. Assign one "
            "or more independent reviewers whose profile explicitly indicates the "
            "required expertise; reviewers and participants must be different people. "
            "Describe required_expertise using expertise held by at least one eligible "
            "independent reviewer, not expertise held only by a participant. "
            "Use only exact supplied member IDs. Return no conflicts when evidence or "
            "team expertise is insufficient."
        )
        payload = {
            "new_entry_ids": [entry["id"] for entry in new_entries],
            "ir_entries": [
                {
                    "id": entry["id"],
                    "author": entry.get("author"),
                    "content": entry.get("content", {}),
                }
                for entry in supplied_entries
            ],
            "project_members": [
                {
                    "id": member["id"],
                    "username": member.get("username"),
                    "profile": member.get("content", {}),
                }
                for member in members
            ],
            "open_issues": [
                {
                    "id": issue["id"],
                    "title": issue["title"],
                    "source_entry_ids": issue.get("source_entry_ids", []),
                }
                for issue in open_issues
            ],
        }
        try:
            response = client.chat.parse(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(payload, ensure_ascii=False),
                    },
                ],
                response_format=ConflictBatch,
                temperature=0,
                max_tokens=4000,
            )
            batch = self._parsed_response(response, ConflictBatch)
        except Exception as exc:
            raise MistralProcessingError(
                self._api_error_message(exc, "check this change for conflicts")
            ) from exc

        new_ids = {entry["id"] for entry in new_entries}
        existing_ids = {entry["id"] for entry in selected_existing}
        entries_by_id = {entry["id"]: entry for entry in supplied_entries}
        member_ids = {member["id"] for member in members}
        open_evidence = {
            frozenset(issue.get("source_entry_ids", []))
            for issue in open_issues
            if issue.get("status") == "open"
        }
        seen_evidence: set[frozenset[str]] = set()
        conflicts = []
        for draft in batch.conflicts:
            source_ids = list(dict.fromkeys(draft.conflicting_entry_ids))
            evidence_key = frozenset(source_ids)
            if (
                not evidence_key
                or not evidence_key <= entries_by_id.keys()
                or not evidence_key & new_ids
                or not evidence_key & existing_ids
                or evidence_key in open_evidence
                or evidence_key in seen_evidence
            ):
                continue

            participants = [
                user_id
                for user_id in dict.fromkeys(draft.participant_ids)
                if user_id in member_ids
            ]
            for entry_id in source_ids:
                author_id = entries_by_id[entry_id].get("author")
                if author_id in member_ids and author_id not in participants:
                    participants.append(author_id)
            reviewers = [
                user_id
                for user_id in dict.fromkeys(draft.reviewer_ids)
                if user_id in member_ids and user_id not in participants
            ]
            if not reviewers:
                reviewers = self._fallback_reviewers(
                    draft.title,
                    draft.summary,
                    draft.required_expertise,
                    members,
                    participants,
                )
            if not participants or not reviewers:
                continue

            seen_evidence.add(evidence_key)
            conflicts.append(
                {
                    "title": draft.title.strip(),
                    "summary": draft.summary.strip(),
                    "conflict_type": draft.conflict_type,
                    "required_expertise": draft.required_expertise.strip(),
                    "source_entry_ids": source_ids,
                    "reviewer_ids": reviewers,
                    "participant_ids": participants,
                }
            )
        return conflicts

    @classmethod
    def _fallback_reviewers(
        cls,
        title: str,
        summary: str,
        required_expertise: str,
        members: list[dict[str, Any]],
        participant_ids: list[str],
    ) -> list[str]:
        """Recover from an overlapping model assignment using profile evidence."""
        ignored_terms = {
            "change",
            "conflict",
            "entry",
            "existing",
            "expertise",
            "project",
            "requirement",
            "review",
            "solution",
        }
        query_terms = {
            term
            for term in cls._normalise(
                f"{title} {summary} {required_expertise}"
            ).split()
            if len(term) > 3 and term not in ignored_terms
        }
        participants = set(participant_ids)
        ranked = []
        for member in members:
            if member["id"] in participants:
                continue
            profile_text = json.dumps(
                member.get("content", {}),
                ensure_ascii=False,
            )
            profile_terms = set(cls._normalise(profile_text).split())
            score = len(query_terms & profile_terms)
            if score:
                ranked.append((score, member["id"]))
        if not ranked:
            return []
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [ranked[0][1]]

    def answer_question(
        self,
        question: str,
        entries: list[dict[str, Any]],
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        client = self._get_client()
        selected_entries = self._select_relevant_entries(question, entries)
        ir_payload = [
            {"id": entry["id"], "content": entry["content"]}
            for entry in selected_entries
        ]
        recent_history = [
            item
            for item in (history or [])[-6:]
            if isinstance(item, dict)
            and item.get("role") in {"user", "assistant"}
            and isinstance(item.get("content"), str)
        ]

        system_prompt = (
            "You answer questions against a project's Intermediate Representation "
            "(IR). The IR is the only source of truth. Do not use outside knowledge "
            "and do not infer facts that are absent. Cite every factual claim using "
            "the exact IR entry IDs supplied. If the answer is not supported, say "
            "what is missing and set insufficient_evidence to true. Never invent an "
            "entry ID."
        )
        user_payload = {
            "question": question,
            "recent_conversation": recent_history,
            "ir_entries": ir_payload,
        }

        try:
            response = client.chat.parse(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": json.dumps(user_payload, ensure_ascii=False),
                    },
                ],
                response_format=GroundedAnswerDraft,
                temperature=0,
                max_tokens=1600,
            )
            draft = self._parsed_response(response, GroundedAnswerDraft)
        except Exception as exc:
            raise MistralProcessingError(
                self._api_error_message(exc, "answer that question")
            ) from exc

        entries_by_id = {entry["id"]: entry for entry in entries}
        valid_ids = list(
            dict.fromkeys(
                entry_id
                for entry_id in draft.citation_ids
                if entry_id in entries_by_id
            )
        )

        if not draft.insufficient_evidence and not valid_ids:
            return {
                "answer": (
                    "I couldn't find enough grounded information in this project's "
                    "IR to answer that."
                ),
                "insufficient_evidence": True,
                "citations": [],
                "model": self.chat_model,
            }

        citations = [
            {
                "entry_id": entry_id,
                "statement": entries_by_id[entry_id]["content"].get(
                    "statement", ""
                ),
                "page": entries_by_id[entry_id]["content"]
                .get("source", {})
                .get("page"),
                "filename": entries_by_id[entry_id]["content"]
                .get("source", {})
                .get("filename"),
                "document_id": entries_by_id[entry_id]["content"]
                .get("source", {})
                .get("document_id"),
                "quote": entries_by_id[entry_id]["content"]
                .get("source", {})
                .get("quote", ""),
            }
            for entry_id in valid_ids
        ]
        return {
            "answer": draft.answer,
            "insufficient_evidence": draft.insufficient_evidence,
            "citations": citations,
            "model": self.chat_model,
        }

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not self.api_key:
            raise MistralConfigurationError(
                "MISTRAL_API_KEY is not configured on the server."
            )
        try:
            from mistralai.client import Mistral

            self._client = Mistral(api_key=self.api_key)
        except Exception as exc:
            raise MistralConfigurationError(
                "The Mistral client could not be initialized."
            ) from exc
        return self._client

    @staticmethod
    def _read_pages(response: Any) -> list[dict[str, Any]]:
        pages = []
        for fallback_index, page in enumerate(getattr(response, "pages", [])):
            page_index = getattr(page, "index", fallback_index)
            markdown = getattr(page, "markdown", "") or ""
            if markdown.strip():
                pages.append(
                    {
                        "page": int(page_index) + 1,
                        "markdown": markdown.strip(),
                    }
                )
        return pages

    def _page_chunks(
        self,
        pages: list[dict[str, Any]],
    ) -> Iterable[list[dict[str, Any]]]:
        chunk: list[dict[str, Any]] = []
        chunk_size = 0
        for page in pages:
            page_size = len(page["markdown"])
            if chunk and chunk_size + page_size > self.chunk_characters:
                yield chunk
                chunk = []
                chunk_size = 0
            chunk.append(page)
            chunk_size += page_size
        if chunk:
            yield chunk

    def _extract_chunk(
        self,
        client: Any,
        pages: list[dict[str, Any]],
    ) -> list[ExtractedFact]:
        page_text = "\n\n".join(
            f"<page number=\"{page['page']}\">\n{page['markdown']}\n</page>"
            for page in pages
        )
        system_prompt = (
            "Convert document text into a neutral Intermediate Representation. "
            "Create atomic facts: one independently useful claim per entry. Extract "
            "only facts explicitly present in the supplied pages. Preserve precise "
            "names, quantities, dates, requirements, decisions, actions, changes, "
            "risks, and constraints. Each entry must use source kind 'document', "
            "include the one-indexed page number, and include a short verbatim "
            "supporting quote. Do not add implications, recommendations, or outside "
            "knowledge. Prefer fewer complete facts over many fragments."
        )
        try:
            response = client.chat.parse(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": page_text},
                ],
                response_format=ExtractionBatch,
                temperature=0,
                max_tokens=8000,
            )
            result = self._parsed_response(response, ExtractionBatch)
            return result.entries
        except Exception as exc:
            raise MistralProcessingError(
                self._api_error_message(exc, "generate structured IR")
            ) from exc

    @staticmethod
    def _api_error_message(error: Exception, operation: str) -> str:
        status = getattr(error, "status_code", None)
        if status == 401:
            return (
                "Mistral rejected MISTRAL_API_KEY (401 Unauthorized). Generate "
                "a new inference API key in Mistral Studio, update backend/.env, "
                "and restart the backend."
            )
        if status == 402:
            return (
                "Mistral requires an active payment method for this request "
                "(402 Payment Required). Check the workspace billing settings."
            )
        if status == 403:
            return (
                "This Mistral API key does not have access to the requested model "
                "(403 Forbidden). Check the key's workspace and model access."
            )
        if status == 413:
            return (
                "Mistral rejected the document because its request was too large. "
                "Try a smaller or compressed file."
            )
        if status == 429:
            return (
                "Mistral's rate limit was reached (429). Wait briefly and try "
                "again."
            )

        detail = MistralDocumentService._safe_error_detail(error)
        suffix = f" Mistral said: {detail}" if detail else ""
        status_label = f" ({status})" if status else ""
        return f"Mistral could not {operation}{status_label}.{suffix}"

    @staticmethod
    def _safe_error_detail(error: Exception) -> str:
        body = getattr(error, "body", None)
        if not isinstance(body, str) or not body:
            return ""
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return ""
        if not isinstance(payload, dict):
            return ""
        detail = payload.get("message") or payload.get("detail")
        if not isinstance(detail, str):
            return ""
        return detail[:500]

    @staticmethod
    def _parsed_response(response: Any, response_model):
        message = response.choices[0].message
        parsed = getattr(message, "parsed", None)
        if parsed is not None:
            if isinstance(parsed, response_model):
                return parsed
            return response_model.model_validate(parsed)

        content = getattr(message, "content", "")
        if not isinstance(content, str):
            raise ValueError("Mistral returned an unexpected response.")
        return response_model.model_validate_json(content)

    @classmethod
    def _ground_facts(
        cls,
        facts: list[ExtractedFact],
        pages: list[dict[str, Any]],
    ) -> list[ExtractedFact]:
        page_text = {
            page["page"]: cls._normalise(page["markdown"]) for page in pages
        }
        result: list[ExtractedFact] = []
        seen: set[str] = set()
        for fact in facts:
            quote = cls._normalise(fact.source.quote)
            statement = cls._normalise(fact.statement)
            if (
                fact.source.kind != "document"
                or fact.source.page is None
                or len(quote) < 3
                or quote not in page_text.get(fact.source.page, "")
                or statement in seen
            ):
                continue
            seen.add(statement)
            result.append(fact)
        return result

    @classmethod
    def _ground_message_facts(
        cls,
        facts: list[ExtractedFact],
        message: str,
    ) -> list[ExtractedFact]:
        source_text = cls._normalise(message)
        result = []
        seen: set[str] = set()
        for fact in facts:
            quote = cls._normalise(fact.source.quote)
            statement = cls._normalise(fact.statement)
            if (
                fact.source.kind != "message"
                or fact.source.page is not None
                or len(quote) < 3
                or quote not in source_text
                or statement in seen
            ):
                continue
            seen.add(statement)
            result.append(fact)
        return result

    @staticmethod
    def _normalise(value: str) -> str:
        return re.sub(r"[\W_]+", " ", value.casefold()).strip()

    @classmethod
    def _select_relevant_entries(
        cls,
        question: str,
        entries: list[dict[str, Any]],
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if len(entries) <= limit:
            return entries

        stop_words = {
            "a",
            "an",
            "and",
            "are",
            "can",
            "did",
            "do",
            "does",
            "for",
            "from",
            "how",
            "i",
            "in",
            "is",
            "it",
            "of",
            "on",
            "the",
            "to",
            "was",
            "what",
            "when",
            "where",
            "which",
            "who",
            "why",
            "with",
        }
        query_terms = {
            term
            for term in cls._normalise(question).split()
            if term not in stop_words and len(term) > 2
        }

        def score(entry: dict[str, Any]) -> int:
            content = json.dumps(entry.get("content", {}), ensure_ascii=False)
            entry_terms = set(cls._normalise(content).split())
            return len(query_terms & entry_terms)

        ranked = sorted(
            enumerate(entries),
            key=lambda pair: (score(pair[1]), -pair[0]),
            reverse=True,
        )
        return [entry for _, entry in ranked[:limit]]
