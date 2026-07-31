from pathlib import Path

from seed import MEDGUARD_PROJECT_ID, seed_medguard
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
    assert len(store.get_bundle(MEDGUARD_PROJECT_ID)["entries"]) == 3
