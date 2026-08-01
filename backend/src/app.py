import os

from dotenv import load_dotenv
from flask import Flask, jsonify
from flask_cors import CORS

from ai.documents.extract import MAX_BYTES
from data import store
from data.seed import seed_medguard
from routes import auth, pipeline, profiles, projects

load_dotenv()

# Vite picks the next free port when 5173 is taken (often 5174). Same host as
# the API (localhost) so the session cookie is same-site and SameSite=Lax works.
_DEFAULT_ORIGINS = (
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
)


def _frontend_origins() -> list[str]:
    configured = os.environ.get("FRONTEND_ORIGIN", "").strip()
    if not configured:
        return list(_DEFAULT_ORIGINS)
    # Comma-separated override; still keeps the defaults so a second Vite
    # instance doesn't break login mid-demo.
    extra = [o.strip() for o in configured.split(",") if o.strip()]
    return list(dict.fromkeys([*_DEFAULT_ORIGINS, *extra]))


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")
    # Refused by Flask before the body is buffered, so an oversized upload costs
    # nothing. The document reader checks the same ceiling again with a message
    # that names it — this one is the backstop, not the explanation.
    app.config["MAX_CONTENT_LENGTH"] = MAX_BYTES + 1024 * 1024
    store.init_db(os.environ.get("DATABASE_PATH"))
    CORS(app, origins=_frontend_origins(), supports_credentials=True)

    app.register_blueprint(auth.bp)
    app.register_blueprint(profiles.bp)
    app.register_blueprint(projects.bp)
    app.register_blueprint(pipeline.bp)

    @app.errorhandler(413)
    def too_large(_error):
        # Every other error this API returns is JSON with an "error" key; a bare
        # HTML 413 would surface in the UI as "Something went wrong".
        return jsonify({"error": f"That file is over {MAX_BYTES // (1024 * 1024)} MB."}), 413

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()

if __name__ == "__main__":
    # Seeding lives here, not at import time, so tests get a clean store.
    seed_medguard()
    # use_reloader=False: the reloader re-execs this module in a subprocess,
    # which would seed the in-memory store twice.
    # 5001, not 5000: macOS AirPlay Receiver squats on port 5000.
    app.run(debug=True, use_reloader=False, port=int(os.environ.get("PORT", 5001)))
