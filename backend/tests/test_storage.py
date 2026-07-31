from pathlib import Path

import pytest

from storage import JsonStore, PermissionDeniedError


@pytest.fixture()
def store(tmp_path: Path):
    return JsonStore(
        tmp_path / "data",
        Path(__file__).resolve().parents[1] / "schemas",
    )


def test_admin_promotion_is_enforced(store: JsonStore):
    store.create_profile({"name": "Admin"}, profile_id="user_admin")
    store.create_profile({"name": "Member"}, profile_id="user_member")
    project = store.create_project(
        "Project",
        "user_admin",
        member_ids=["user_member"],
    )

    with pytest.raises(PermissionDeniedError):
        store.promote_member(
            project["id"],
            "user_member",
            "user_member",
        )

    promoted = store.promote_member(
        project["id"],
        "user_admin",
        "user_member",
    )
    assert promoted["admins"] == ["user_admin", "user_member"]


def test_last_admin_exit_auto_promotes_remaining_member(store: JsonStore):
    store.create_profile({"name": "Admin"}, profile_id="user_admin")
    store.create_profile({"name": "Member"}, profile_id="user_member")
    project = store.create_project(
        "Project",
        "user_admin",
        member_ids=["user_member"],
    )

    updated = store.exit_project(project["id"], "user_admin")

    assert updated["users"] == ["user_member"]
    assert updated["admins"] == ["user_member"]


def test_only_admins_can_add_and_remove_members(store: JsonStore):
    store.create_profile({"name": "Admin"}, profile_id="user_admin")
    store.create_profile({"name": "Member"}, profile_id="user_member")
    store.create_profile({"name": "Other"}, profile_id="user_other")
    project = store.create_project(
        "Project",
        "user_admin",
        member_ids=["user_member"],
    )

    with pytest.raises(PermissionDeniedError):
        store.add_member(project["id"], "user_member", "user_other")

    added = store.add_member(project["id"], "user_admin", "user_other")
    assert "user_other" in added["users"]

    removed = store.remove_member(
        project["id"],
        "user_admin",
        "user_member",
    )
    assert "user_member" not in removed["users"]


def test_new_entries_have_version_history(store: JsonStore):
    store.create_profile({"name": "Author"}, profile_id="user_author")
    project = store.create_project("Project", "user_author")
    entry = store.append_entries(
        project["id"],
        [{"statement": "A grounded fact."}],
        "user_author",
    )[0]

    versions = store.get_versions(entry["id"])

    assert len(versions) == 1
    assert versions[0]["content"]["statement"] == "A grounded fact."
