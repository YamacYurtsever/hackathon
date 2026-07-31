"""Tests for what persistence actually buys: state that outlives the process."""

from data import store
from data.seed import EXAMPLE_PROFILES, seed_medguard


def test_data_survives_a_reconnect(tmp_path):
    # The point of the whole milestone: a restart must not wipe the project.
    path = str(tmp_path / "restart.db")
    store.init_db(path)

    profile = store.create_profile("ada", "hash", {"description": "engineer"})
    project = store.create_project("MedGuard", creator_id=profile["id"])
    entry = store.create_entry({"statement": "Sampling is 2 kHz."}, author=profile["id"])
    store.add_entry_to_project(project["id"], entry["id"])

    # Simulate a fresh process pointed at the same file.
    store.init_db(path)

    reloaded = store.get_project(project["id"])
    assert reloaded["name"] == "MedGuard"
    assert reloaded["users"] == [profile["id"]]
    assert reloaded["admins"] == [profile["id"]]
    assert reloaded["ir"] == [entry["id"]]

    assert store.get_profile(profile["id"])["content"] == {"description": "engineer"}
    assert store.get_entry(entry["id"])["content"] == {"statement": "Sampling is 2 kHz."}


def test_entry_order_is_stable(tmp_path):
    # The feed reads chronologically, so insertion order has to survive.
    store.init_db(str(tmp_path / "order.db"))
    profile = store.create_profile("ada", "hash", {})
    project = store.create_project("P", creator_id=profile["id"])

    ids = []
    for index in range(5):
        entry = store.create_entry({"statement": f"fact {index}"}, author=profile["id"])
        store.add_entry_to_project(project["id"], entry["id"])
        ids.append(entry["id"])

    assert store.get_project(project["id"])["ir"] == ids


def test_member_order_is_stable(tmp_path):
    # Auto-promotion picks the longest-standing member, so order matters here too.
    store.init_db(str(tmp_path / "members.db"))
    owner = store.create_profile("owner", "hash", {})
    project = store.create_project("P", creator_id=owner["id"])

    joiners = [store.create_profile(f"u{index}", "hash", {}) for index in range(3)]
    for joiner in joiners:
        store.add_member(project["id"], joiner["id"])

    expected = [owner["id"]] + [joiner["id"] for joiner in joiners]
    assert store.get_project(project["id"])["users"] == expected


def test_deleting_a_project_cleans_up_its_rows(tmp_path):
    # Membership and entry links are cascaded, so nothing dangles behind.
    store.init_db(str(tmp_path / "cascade.db"))
    profile = store.create_profile("ada", "hash", {})
    project = store.create_project("P", creator_id=profile["id"])
    entry = store.create_entry({"statement": "x"}, author=profile["id"])
    store.add_entry_to_project(project["id"], entry["id"])

    assert store.remove_member(project["id"], profile["id"]) is None
    assert store.get_project(project["id"]) is None
    assert store.projects_for_user(profile["id"]) == []


def test_profile_content_update_persists(tmp_path):
    # Mutating a returned dict no longer writes anything — this is the setter
    # that replaced that.
    store.init_db(str(tmp_path / "profile.db"))
    profile = store.create_profile("ada", "hash", {"description": "old"})

    store.update_profile_content(profile["id"], {"description": "new"})

    assert store.get_profile(profile["id"])["content"] == {"description": "new"}


def test_seeding_twice_does_not_duplicate(tmp_path):
    # The database outlives the process now, so booting twice must not pile up
    # a second set of MedGuard accounts.
    store.init_db(str(tmp_path / "seed.db"))

    first = seed_medguard()
    assert first is not None

    assert seed_medguard() is None

    profile = store.find_profile_by_username(EXAMPLE_PROFILES[0]["username"])
    assert len(store.projects_for_user(profile["id"])) == 1


def test_default_db_path_is_the_backend_root():
    # It's derived from this module's location, so moving store.py between
    # packages would otherwise relocate everyone's database without a word.
    import os

    assert os.path.basename(store.DEFAULT_PATH) == "data.db"
    assert os.path.basename(os.path.dirname(store.DEFAULT_PATH)) == "backend"
