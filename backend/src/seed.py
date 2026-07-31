from werkzeug.security import generate_password_hash

import store

EXAMPLE_PROFILES = [
    {
        "username": "engineer",
        "content": {
            "role": "engineer",
            "expertise": ["signal processing", "embedded firmware"],
            "history_summary": "Owns the sensor and firmware design for MedGuard.",
        },
    },
    {
        "username": "biologist",
        "content": {
            "role": "biologist",
            "expertise": ["assay validation", "false-positive analysis"],
            "history_summary": "Runs the validation studies MedGuard's detection relies on.",
        },
    },
    {
        "username": "lawyer",
        "content": {
            "role": "lawyer",
            "expertise": ["FDA 510(k) submissions", "medical device regulation"],
            "history_summary": "Manages MedGuard's regulatory filings.",
        },
    },
    {
        "username": "business",
        "content": {
            "role": "business",
            "expertise": ["timeline and budget planning"],
            "history_summary": "Tracks MedGuard's launch timeline and cost.",
        },
    },
]

# Demo-only: every seeded account shares this password.
SEED_PASSWORD = "medguard"


def seed_medguard() -> dict:
    password_hash = generate_password_hash(SEED_PASSWORD)
    created_profiles = [
        store.create_profile(profile["username"], password_hash, profile["content"])
        for profile in EXAMPLE_PROFILES
    ]
    project = store.create_project("MedGuard", creator_id=created_profiles[0]["id"])
    for profile in created_profiles[1:]:
        store.add_member(project["id"], profile["id"])
    return project


if __name__ == "__main__":
    seeded_project = seed_medguard()
    print(f"Created project {seeded_project['id']!r} with users {seeded_project['users']}")
