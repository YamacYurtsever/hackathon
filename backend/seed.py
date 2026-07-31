import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from storage import JsonStore, RecordNotFoundError

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

MEDGUARD_PROJECT_ID = "prj_medguard"
MEDGUARD_PROFILES: dict[str, dict[str, Any]] = {
    "user_engineer": {
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
]


def seed_medguard(store: JsonStore) -> dict[str, Any]:
    for profile_id, content in MEDGUARD_PROFILES.items():
        try:
            store.get_profile(profile_id)
        except RecordNotFoundError:
            store.create_profile(content, profile_id=profile_id)

    try:
        project = store.get_project(MEDGUARD_PROJECT_ID)
    except RecordNotFoundError:
        project = store.create_project(
            "MedGuard",
            "user_engineer",
            project_id=MEDGUARD_PROJECT_ID,
            member_ids=[
                "user_biologist",
                "user_regulatory",
                "user_business",
            ],
        )
        store.append_entries(
            project["id"],
            MEDGUARD_FACTS,
            "user_engineer",
        )
        project = store.get_project(project["id"])

    return {
        "project": project,
        "profiles": [
            store.get_profile(profile_id)
            for profile_id in MEDGUARD_PROFILES
        ],
    }


def main() -> None:
    store = JsonStore(
        Path(os.environ.get("DATA_DIR", BASE_DIR / "data")),
        BASE_DIR / "schemas",
    )
    result = seed_medguard(store)
    print(
        f"Seeded {result['project']['name']} "
        f"({result['project']['id']}) with "
        f"{len(result['profiles'])} profiles."
    )


if __name__ == "__main__":
    main()
