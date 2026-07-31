def test_create_project_makes_creator_the_only_admin(client, signed_up):
    creator = signed_up("ada")

    response = client.post("/api/projects", json={"name": "MedGuard"})

    assert response.status_code == 201
    project = response.get_json()
    assert project["name"] == "MedGuard"
    assert project["users"] == [creator["id"]]
    assert project["admins"] == [creator["id"]]
    assert project["ir"] == []


def test_create_project_requires_a_name(client, signed_up):
    signed_up("ada")
    assert client.post("/api/projects", json={"name": "  "}).status_code == 400


def test_list_projects_only_returns_your_own(client, signed_up):
    signed_up("ada")
    client.post("/api/projects", json={"name": "Mine"})
    client.post("/api/logout")

    signed_up("bob")
    assert client.get("/api/projects").get_json() == []

    client.post("/api/projects", json={"name": "Bob's"})
    assert [p["name"] for p in client.get("/api/projects").get_json()] == ["Bob's"]


def test_available_projects_excludes_ones_you_are_in(client, signed_up):
    signed_up("ada")
    client.post("/api/projects", json={"name": "Ada's"})
    assert client.get("/api/projects/available").get_json() == []

    client.post("/api/logout")
    signed_up("bob")
    assert [p["name"] for p in client.get("/api/projects/available").get_json()] == ["Ada's"]


def test_non_member_cannot_read_a_project(client, signed_up):
    signed_up("ada")
    project = client.post("/api/projects", json={"name": "Private"}).get_json()
    client.post("/api/logout")

    signed_up("bob")
    assert client.get(f"/api/projects/{project['id']}").status_code == 403


def test_joining_grants_membership_but_not_admin(client, signed_up):
    ada = signed_up("ada")
    project = client.post("/api/projects", json={"name": "Shared"}).get_json()
    client.post("/api/logout")

    bob = signed_up("bob")
    response = client.post(f"/api/projects/{project['id']}/join")

    assert response.status_code == 200
    joined = response.get_json()
    assert set(joined["users"]) == {ada["id"], bob["id"]}
    # Joining must never hand out admin rights.
    assert joined["admins"] == [ada["id"]]


def test_member_can_read_project_after_joining(client, signed_up):
    signed_up("ada")
    project = client.post("/api/projects", json={"name": "Shared"}).get_json()
    client.post("/api/logout")

    signed_up("bob")
    client.post(f"/api/projects/{project['id']}/join")
    assert client.get(f"/api/projects/{project['id']}").status_code == 200


def test_joining_twice_does_not_duplicate_membership(client, signed_up):
    signed_up("ada")
    project = client.post("/api/projects", json={"name": "Shared"}).get_json()
    client.post("/api/logout")

    signed_up("bob")
    client.post(f"/api/projects/{project['id']}/join")
    joined = client.post(f"/api/projects/{project['id']}/join").get_json()

    assert len(joined["users"]) == 2


def test_joining_missing_project_404s(client, signed_up):
    signed_up("ada")
    assert client.post("/api/projects/nope/join").status_code == 404


def test_project_endpoints_require_login(client):
    assert client.get("/api/projects").status_code == 401
    assert client.get("/api/projects/available").status_code == 401
    assert client.post("/api/projects", json={"name": "x"}).status_code == 401
    assert client.get("/api/projects/any").status_code == 401
    assert client.post("/api/projects/any/join").status_code == 401
