def test_signup_creates_profile_with_empty_content(client):
    response = client.post("/api/signup", json={"username": "ada", "password": "pw"})

    assert response.status_code == 201
    body = response.get_json()
    assert body["username"] == "ada"
    # Self-description is filled in from the app later, not at signup.
    assert body["content"] == {}


def test_signup_never_returns_password_hash(client):
    response = client.post("/api/signup", json={"username": "ada", "password": "pw"})
    assert "password_hash" not in response.get_json()


def test_signup_logs_you_in(client, signed_up):
    signed_up("ada")
    assert client.get("/api/me").status_code == 200


def test_signup_requires_username_and_password(client):
    assert client.post("/api/signup", json={"username": "", "password": ""}).status_code == 400


def test_signup_rejects_duplicate_username(client, signed_up):
    signed_up("ada")
    response = client.post("/api/signup", json={"username": "ada", "password": "other"})
    assert response.status_code == 409


def test_login_with_correct_password(client, signed_up):
    signed_up("ada", "hunter2")
    client.post("/api/logout")

    response = client.post("/api/login", json={"username": "ada", "password": "hunter2"})
    assert response.status_code == 200
    assert "password_hash" not in response.get_json()


def test_login_rejects_wrong_password(client, signed_up):
    signed_up("ada", "hunter2")
    client.post("/api/logout")

    response = client.post("/api/login", json={"username": "ada", "password": "nope"})
    assert response.status_code == 401


def test_login_rejects_unknown_user(client):
    response = client.post("/api/login", json={"username": "ghost", "password": "pw"})
    assert response.status_code == 401


def test_logout_ends_the_session(client, signed_up):
    signed_up("ada")
    assert client.post("/api/logout").status_code == 204
    assert client.get("/api/me").status_code == 401


def test_me_requires_login(client):
    assert client.get("/api/me").status_code == 401


def test_get_profile_requires_login(client, signed_up):
    profile = signed_up("ada")
    client.post("/api/logout")
    assert client.get(f"/api/profiles/{profile['id']}").status_code == 401


def test_get_missing_profile_404s(client, signed_up):
    signed_up("ada")
    assert client.get("/api/profiles/nope").status_code == 404


def test_update_own_profile_content(client, signed_up):
    signed_up("ada")

    response = client.put("/api/profiles/me", json={"content": {"description": "biologist"}})

    assert response.status_code == 200
    assert response.get_json()["content"] == {"description": "biologist"}
    # And it persists.
    assert client.get("/api/me").get_json()["content"] == {"description": "biologist"}


def test_update_profile_rejects_non_object_content(client, signed_up):
    signed_up("ada")
    assert client.put("/api/profiles/me", json={"content": "a string"}).status_code == 400


def test_update_profile_requires_login(client):
    assert client.put("/api/profiles/me", json={"content": {}}).status_code == 401
