import os

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

from seed import seed_medguard

load_dotenv()


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app)

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
seed_medguard()

if __name__ == "__main__":
    # use_reloader=False: the reloader re-execs this module in a subprocess,
    # which would seed the in-memory store twice.
    app.run(debug=True, use_reloader=False, port=int(os.environ.get("PORT", 5000)))
