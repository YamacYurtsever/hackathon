import os

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from data import store
from data.seed import seed_medguard
from routes import auth, pipeline, profiles, projects

load_dotenv()

# Vite dev server. Same host as the API (localhost) so the session cookie is
# same-site and SameSite=Lax works without loosening anything.
FRONTEND_ORIGIN = "http://localhost:5173"


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")
    store.init_db(os.environ.get("DATABASE_PATH"))
    CORS(app, origins=[FRONTEND_ORIGIN], supports_credentials=True)

    app.register_blueprint(auth.bp)
    app.register_blueprint(profiles.bp)
    app.register_blueprint(projects.bp)
    app.register_blueprint(pipeline.bp)

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
