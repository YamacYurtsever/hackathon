from pathlib import Path

from seed import (
    MEDGUARD_PROJECT_ID,
    reset_and_seed_medguard,
    seed_medguard,
)
from storage import JsonStore


def test_medguard_seed_is_complete_and_idempotent(tmp_path: Path):
    store = JsonStore(
        tmp_path / "data",
        Path(__file__).resolve().parents[1] / "schemas",
    )

    first = seed_medguard(store)
    second = seed_medguard(store)

    assert first["project"]["id"] == MEDGUARD_PROJECT_ID
    assert second["project"]["id"] == MEDGUARD_PROJECT_ID
    assert len(first["profiles"]) == 4
    assert len(first["project"]["users"]) == 4
    assert first["project"]["admins"] == ["user_engineer"]
    entries = store.get_bundle(MEDGUARD_PROJECT_ID)["entries"]
    assert len(entries) == 4
    assert any(
        "once every ten seconds" in entry["content"]["statement"]
        for entry in entries
    )


def test_medguard_seed_restores_members_who_exited(tmp_path: Path):
    store = JsonStore(
        tmp_path / "data",
        Path(__file__).resolve().parents[1] / "schemas",
    )
    seed_medguard(store)
    store.exit_project(MEDGUARD_PROJECT_ID, "user_business")
    store.exit_project(MEDGUARD_PROJECT_ID, "user_engineer")

    restored = seed_medguard(store)["project"]

    assert set(restored["users"]) == {
        "user_engineer",
        "user_biologist",
        "user_regulatory",
        "user_business",
    }
    assert "user_engineer" in restored["admins"]
    assert len(store.get_bundle(MEDGUARD_PROJECT_ID)["entries"]) == 4


def test_reset_seed_deletes_all_records_before_recreating_medguard(
    tmp_path: Path,
):
    store = JsonStore(
        tmp_path / "data",
        Path(__file__).resolve().parents[1] / "schemas",
    )
    seed_medguard(store)
    store.create_profile(
        {"name": "Temporary member"},
        profile_id="user_temporary",
    )
    temporary_project = store.create_project(
        "Temporary project",
        "user_temporary",
    )
    store.append_entries(
        temporary_project["id"],
        [{"statement": "Temporary fact."}],
        "user_temporary",
    )

    result = reset_and_seed_medguard(store)

    assert result["removed_records"] > 0
    assert [project["id"] for project in store.list_projects()] == [
        MEDGUARD_PROJECT_ID
    ]
    assert {profile["id"] for profile in store.list_profiles()} == {
        "user_engineer",
        "user_biologist",
        "user_regulatory",
        "user_business",
    }
    assert len(store.get_bundle(MEDGUARD_PROJECT_ID)["entries"]) == 4
    assert list(store.documents_dir.iterdir()) == []
    assert list(store.issues_dir.iterdir()) == []
