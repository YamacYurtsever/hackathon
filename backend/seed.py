import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from storage import JsonStore, RecordNotFoundError

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

MEDGUARD_PROJECT_ID = "prj_medguard"
MEDGUARD_PASSWORD = "medguard"
MEDGUARD_MEMBER_IDS = (
    "user_engineer",
    "user_biologist",
    "user_regulatory",
    "user_business",
)
MEDGUARD_PROFILES: dict[str, dict[str, Any]] = {
    "user_engineer": {
        "username": "engineer",
        "name": "Maya Chen",
        "discipline": "Embedded systems engineering",
        "expertise": (
            "Signal acquisition, sensor firmware, debounce filters, and design "
            "verification for clinical devices."
        ),
        "history": "Owns the MedGuard sensor and firmware implementation.",
        "preferences": "Precise technical language, concrete failure modes, and units.",
    },
    "user_biologist": {
        "username": "biologist",
        "name": "Dr. Sam Okafor",
        "discipline": "Clinical biology",
        "expertise": (
            "False-positive validation, assay design, clinical study protocols, "
            "and interpreting sensitivity/specificity trade-offs."
        ),
        "history": "Owns biological validation for MedGuard.",
        "preferences": "Frame changes in terms of study validity and evidence quality.",
    },
    "user_regulatory": {
        "username": "lawyer",
        "name": "Elena Rossi",
        "discipline": "Medical-device regulatory law",
        "expertise": (
            "FDA 510(k) submissions, design controls, change assessment, and "
            "traceable regulatory documentation."
        ),
        "history": "Prepared the current MedGuard submission package.",
        "preferences": "Surface filing, documentation, and compliance implications.",
    },
    "user_business": {
        "username": "business",
        "name": "Marcus Reed",
        "discipline": "Business operations",
        "expertise": (
            "Clinical-device delivery planning, supplier coordination, budgets, "
            "and launch risk."
        ),
        "history": "Owns the MedGuard launch plan and operating budget.",
        "preferences": "Translate technical changes into schedule, cost, and risk.",
    },
}

MEDGUARD_FACTS = [
    {
        "statement": "The sensor sampling rate was increased to 2 kHz.",
        "category": "change",
        "entities": ["sensor", "sampling rate", "2 kHz"],
        "source": {
            "kind": "message",
            "page": None,
            "quote": "Bumped sampling rate to 2kHz",
        },
        "confidence": "high",
    },
    {
        "statement": "A debounce filter was added to the sensor pipeline.",
        "category": "change",
        "entities": ["debounce filter", "sensor pipeline"],
        "source": {
            "kind": "message",
            "page": None,
            "quote": "added debounce filter",
        },
        "confidence": "high",
    },
    {
        "statement": (
            "The sampling and filter changes are expected to reduce false positives."
        ),
        "category": "context",
        "entities": ["false positives", "sampling rate", "debounce filter"],
        "source": {
            "kind": "message",
            "page": None,
            "quote": "should cut false positives",
        },
        "confidence": "medium",
    },
    {
        "statement": (
            "Telemetry upload frequency was changed from once per second to "
            "once every ten seconds."
        ),
        "category": "change",
        "entities": ["telemetry", "upload frequency", "ten seconds"],
        "source": {
            "kind": "message",
            "page": None,
            "quote": "changed telemetry uploads from once per second to every ten seconds",
        },
        "confidence": "high",
    },
]


def seed_medguard(store: JsonStore) -> dict[str, Any]:
    password_hash = generate_password_hash(MEDGUARD_PASSWORD)
    for profile_id, profile_data in MEDGUARD_PROFILES.items():
        content = {
            key: value
            for key, value in profile_data.items()
            if key != "username"
        }
        username = profile_data["username"]
        try:
            store.get_profile(profile_id)
        except RecordNotFoundError:
            store.create_profile(
                content,
                profile_id=profile_id,
                username=username,
                password_hash=password_hash,
            )
        else:
            profile = store.get_profile_for_auth(profile_id)
            if (
                profile.get("username") != username
                or not profile.get("password_hash")
            ):
                store.update_profile_account(
                    profile_id,
                    username=username,
                    password_hash=password_hash,
                )

    try:
        project = store.get_project(MEDGUARD_PROJECT_ID)
    except RecordNotFoundError:
        project = store.create_project(
            "MedGuard",
            "user_engineer",
            project_id=MEDGUARD_PROJECT_ID,
            member_ids=list(MEDGUARD_MEMBER_IDS[1:]),
        )
        store.append_entries(
            project["id"],
            MEDGUARD_FACTS,
            "user_engineer",
        )
        project = store.get_project(project["id"])

    # A demo user may have clicked "Exit project". Re-running the seed should
    # restore access without replacing the project or erasing accumulated IR.
    for profile_id in MEDGUARD_MEMBER_IDS:
        if profile_id not in project["users"]:
            project = store.join_project(MEDGUARD_PROJECT_ID, profile_id)
    if "user_engineer" not in project["admins"]:
        project = store.promote_member(
            MEDGUARD_PROJECT_ID,
            project["admins"][0],
            "user_engineer",
        )

    return {
        "project": project,
        "profiles": [
            store.get_profile(profile_id)
            for profile_id in MEDGUARD_PROFILES
        ],
    }


def reset_and_seed_medguard(store: JsonStore) -> dict[str, Any]:
    """Erase all stored demo records, then recreate only MedGuard."""
    removed_records = store.clear_all_records()
    result = seed_medguard(store)
    return {**result, "removed_records": removed_records}


def main() -> None:
    store = JsonStore(
        Path(os.environ.get("DATA_DIR", BASE_DIR / "data")),
        BASE_DIR / "schemas",
    )
    result = reset_and_seed_medguard(store)
    print(
        f"Reset {result['removed_records']} records and seeded "
        f"{result['project']['name']} "
        f"({result['project']['id']}) with "
        f"{len(result['profiles'])} profiles."
    )


if __name__ == "__main__":
    main()
