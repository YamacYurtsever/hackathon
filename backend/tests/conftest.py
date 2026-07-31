import pytest

from data import store
from app import create_app


@pytest.fixture
def client(tmp_path):
    """Fresh app and its own database file per test, so nothing leaks between
    tests and none of them touch the real data.db."""
    store.init_db(str(tmp_path / "test.db"))

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
