import mimetypes
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename

from mistral_service import (
    MistralConfigurationError,
    MistralDocumentService,
    MistralProcessingError,
)
from storage import JsonStore, RecordNotFoundError

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

MAX_FILE_BYTES = 20 * 1024 * 1024
ALLOWED_EXTENSIONS = {
    ".pdf": "application/pdf",
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
    ".pptx": (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    ),
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".avif": "image/avif",
}


def create_app(
    *,
    service: MistralDocumentService | None = None,
    store: JsonStore | None = None,
    test_config: dict[str, Any] | None = None,
) -> Flask:
    app = Flask(__name__)
    app.config.update(
        MAX_CONTENT_LENGTH=MAX_FILE_BYTES,
        JSON_SORT_KEYS=False,
    )
    if test_config:
        app.config.update(test_config)
    CORS(app)

    document_service = service or MistralDocumentService(
        os.environ.get("MISTRAL_API_KEY", ""),
        ocr_model=os.environ.get("MISTRAL_OCR_MODEL", "mistral-ocr-latest"),
        chat_model=os.environ.get(
            "MISTRAL_CHAT_MODEL",
            "mistral-small-latest",
        ),
    )
    json_store = store or JsonStore(
        Path(os.environ.get("DATA_DIR", BASE_DIR / "data")),
        BASE_DIR / "schemas",
    )

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "mistral_configured": document_service.configured,
        }

    @app.get("/api/documents")
    def list_documents():
        return {"documents": json_store.list_documents()}

    @app.post("/api/documents")
    def create_document():
        uploaded_file = request.files.get("file")
        if uploaded_file is None:
            return _error("Attach a file in the 'file' field.", 400)

        filename = secure_filename(uploaded_file.filename or "")
        extension = Path(filename).suffix.casefold()
        if not filename or extension not in ALLOWED_EXTENSIONS:
            return _error(
                "Use a PDF, DOCX, PPTX, PNG, JPG, WEBP, or AVIF file.",
                415,
            )

        content = uploaded_file.read()
        if not content:
            return _error("The uploaded file is empty.", 400)
        if len(content) > MAX_FILE_BYTES:
            return _error("Files must be 20 MB or smaller.", 413)

        guessed_type = ALLOWED_EXTENSIONS[extension]
        supplied_type = uploaded_file.mimetype
        mime_type = (
            supplied_type
            if supplied_type
            and supplied_type != "application/octet-stream"
            else guessed_type
        )
        if mime_type not in set(ALLOWED_EXTENSIONS.values()):
            mime_type = mimetypes.guess_type(filename)[0] or guessed_type

        result = document_service.process_document(content, mime_type)
        bundle = json_store.create_document(
            filename=filename,
            mime_type=mime_type,
            size_bytes=len(content),
            pages=result["pages"],
            facts=result["facts"],
            ocr_model=result["ocr_model"],
            chat_model=result["chat_model"],
        )
        return jsonify(bundle), 201

    @app.get("/api/projects/<project_id>")
    def get_project(project_id: str):
        return json_store.get_bundle(project_id)

    @app.post("/api/projects/<project_id>/questions")
    def ask_project(project_id: str):
        payload = request.get_json(silent=True) or {}
        if not isinstance(payload, dict):
            return _error("Request body must be a JSON object.", 400)
        question = payload.get("question")
        if not isinstance(question, str) or not question.strip():
            return _error("Question is required.", 400)
        if len(question) > 2000:
            return _error("Question must be 2,000 characters or fewer.", 400)

        history = payload.get("history", [])
        if not isinstance(history, list):
            return _error("History must be a list.", 400)

        bundle = json_store.get_bundle(project_id)
        answer = document_service.answer_question(
            question.strip(),
            bundle["entries"],
            history,
        )
        return {
            **answer,
            "project_id": project_id,
        }

    @app.errorhandler(RecordNotFoundError)
    def handle_not_found(_error_value):
        return _error("That project ID was not found.", 404)

    @app.errorhandler(MistralConfigurationError)
    def handle_configuration_error(error):
        return _error(str(error), 503)

    @app.errorhandler(MistralProcessingError)
    def handle_processing_error(error):
        return _error(str(error), 422)

    @app.errorhandler(RequestEntityTooLarge)
    def handle_file_too_large(_error_value):
        return _error("Files must be 20 MB or smaller.", 413)

    @app.errorhandler(500)
    def handle_server_error(_error_value):
        return _error("Something went wrong on the server.", 500)

    return app


def _error(message: str, status: int):
    return jsonify({"error": message}), status


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
