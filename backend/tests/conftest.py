import pytest

import store
from app import create_app


@pytest.fixture
def client():
    """Fresh app and empty store per test — the store is module-level state."""
    store.profiles.clear()
    store.projects.clear()
    store.entries.clear()

    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


@pytest.fixture
def signed_up(client):
    """Signs up a user and leaves them logged in. Returns their profile."""

    def _signup(username="tester", password="pw"):
        response = client.post(
            "/api/signup", json={"username": username, "password": password}
        )
        assert response.status_code == 201
        return response.get_json()

    return _signup
