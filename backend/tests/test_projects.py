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


def test_invite_preview_shows_only_name_and_id(client, signed_up):
    signed_up("ada")
    project = client.post("/api/projects", json={"name": "Ada's"}).get_json()
    client.post("/api/logout")

    # A non-member following an invite link sees what they're joining...
    signed_up("bob")
    preview = client.get(f"/api/projects/{project['id']}/invite").get_json()
    assert preview == {"id": project["id"], "name": "Ada's"}
    # ...but nothing else about it until they actually join.
    assert "users" not in preview
    assert "ir" not in preview


def test_invite_preview_404s_for_unknown_project(client, signed_up):
    signed_up("ada")
    assert client.get("/api/projects/nope/invite").status_code == 404


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
    assert client.get("/api/projects/any/invite").status_code == 401
    assert client.post("/api/projects", json={"name": "x"}).status_code == 401
    assert client.get("/api/projects/any").status_code == 401
    assert client.post("/api/projects/any/join").status_code == 401


def test_members_list_includes_usernames_and_admin_flags(client, signed_up):
    signed_up("ada")
    project = client.post("/api/projects", json={"name": "Shared"}).get_json()
    client.post("/api/logout")

    signed_up("bob")
    client.post(f"/api/projects/{project['id']}/join")

    members = client.get(f"/api/projects/{project['id']}/members").get_json()
    by_name = {m["username"]: m for m in members}
    assert by_name["ada"]["is_admin"] is True
    assert by_name["bob"]["is_admin"] is False
    assert all("password_hash" not in m for m in members)


def test_non_member_cannot_list_members(client, signed_up):
    signed_up("ada")
    project = client.post("/api/projects", json={"name": "Private"}).get_json()
    client.post("/api/logout")

    signed_up("bob")
    assert client.get(f"/api/projects/{project['id']}/members").status_code == 403


def test_admin_can_promote_a_member(client, signed_up):
    signed_up("ada")
    project = client.post("/api/projects", json={"name": "Shared"}).get_json()
    client.post("/api/logout")

    bob = signed_up("bob")
    client.post(f"/api/projects/{project['id']}/join")
    client.post("/api/logout")

    client.post("/api/login", json={"username": "ada", "password": "pw"})
    response = client.post(
        f"/api/projects/{project['id']}/promote", json={"user_id": bob["id"]}
    )

    assert response.status_code == 200
    assert bob["id"] in response.get_json()["admins"]


def test_non_admin_cannot_promote(client, signed_up):
    signed_up("ada")
    project = client.post("/api/projects", json={"name": "Shared"}).get_json()
    client.post("/api/logout")

    bob = signed_up("bob")
    client.post(f"/api/projects/{project['id']}/join")

    # Bob is a plain member trying to make himself an admin.
    response = client.post(
        f"/api/projects/{project['id']}/promote", json={"user_id": bob["id"]}
    )
    assert response.status_code == 403


def test_cannot_promote_a_non_member(client, signed_up):
    signed_up("ada")
    project = client.post("/api/projects", json={"name": "Shared"}).get_json()

    response = client.post(
        f"/api/projects/{project['id']}/promote", json={"user_id": "stranger"}
    )
    assert response.status_code == 400


def test_exit_removes_you_from_the_project(client, signed_up):
    ada = signed_up("ada")
    project = client.post("/api/projects", json={"name": "Shared"}).get_json()
    client.post("/api/logout")

    signed_up("bob")
    client.post(f"/api/projects/{project['id']}/join")
    response = client.post(f"/api/projects/{project['id']}/exit")

    assert response.status_code == 200
    assert response.get_json()["users"] == [ada["id"]]
    assert client.get("/api/projects").get_json() == []


def test_last_admin_leaving_auto_promotes_a_remaining_member(client, signed_up):
    signed_up("ada")
    project = client.post("/api/projects", json={"name": "Shared"}).get_json()
    client.post("/api/logout")

    bob = signed_up("bob")
    client.post(f"/api/projects/{project['id']}/join")
    client.post("/api/logout")

    client.post("/api/login", json={"username": "ada", "password": "pw"})
    remaining = client.post(f"/api/projects/{project['id']}/exit").get_json()

    # A project with members must never be left without an admin.
    assert remaining["users"] == [bob["id"]]
    assert remaining["admins"] == [bob["id"]]


def test_last_member_leaving_deletes_the_project(client, signed_up):
    signed_up("ada")
    project = client.post("/api/projects", json={"name": "Solo"}).get_json()

    assert client.post(f"/api/projects/{project['id']}/exit").status_code == 204
    # Gone entirely — not left orphaned and joinable with no admin.
    assert client.get(f"/api/projects/{project['id']}").status_code == 404
    assert client.get(f"/api/projects/{project['id']}/invite").status_code == 404


def test_non_member_cannot_exit(client, signed_up):
    signed_up("ada")
    project = client.post("/api/projects", json={"name": "Private"}).get_json()
    client.post("/api/logout")

    signed_up("bob")
    assert client.post(f"/api/projects/{project['id']}/exit").status_code == 403


def test_member_endpoints_require_login(client):
    assert client.get("/api/projects/any/members").status_code == 401
    assert client.post("/api/projects/any/promote", json={}).status_code == 401
    assert client.post("/api/projects/any/exit").status_code == 401
