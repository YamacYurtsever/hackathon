from werkzeug.security import generate_password_hash

import store

# Content is free-form by design — these are just examples of what someone might
# write about themselves. Nothing in the pipeline reads a fixed "role" key. The
# keys that earn their keep are the ones that tell re-projection what to *skip*
# ("assume_i_know", "dont_explain") and what to lead with ("cares_about"):
# filtering is as much a part of re-projection as wording.
EXAMPLE_PROFILES = [
    {
        "username": "engineer",
        "content": {
            "name": "Priya Raman",
            "describes_self_as": "Embedded firmware engineer. Ten years in signal acquisition, mostly biopotential front-ends.",
            "expertise": ["DSP", "ADC design", "firmware", "filter design"],
            "on_this_project": "Owns the sensor front-end and detection firmware. Joined at kickoff.",
            "assume_i_know": "Sampling theory, filter topologies, the device signal chain end to end.",
            "dont_explain": "Anything about DSP or embedded systems.",
        },
    },
    {
        "username": "biologist",
        "content": {
            "name": "Marcus Oyelaran",
            "describes_self_as": "Clinical scientist. I design and run the validation studies that produce our performance claims.",
            "expertise": ["study design", "cardiac physiology", "biostatistics"],
            "on_this_project": "Owns the false-positive characterisation study and the clinical evidence package.",
            "assume_i_know": "Study protocols, arrhythmia physiology, what invalidates a result.",
            "dont_explain": "Statistics or clinical trial methodology.",
            "weak_on": "Firmware and DSP — explain signal chain changes in terms of what they do, not how.",
        },
    },
    {
        "username": "lawyer",
        "content": {
            "name": "Ellen Whitcombe",
            "describes_self_as": "Regulatory counsel, medical devices. Fifteen years of 510(k) and PMA submissions.",
            "expertise": ["FDA device regulation", "21 CFR", "submission strategy"],
            "on_this_project": "Owns the 510(k) submission. Joined three months in.",
            "assume_i_know": "The regulatory framework and what triggers a new submission.",
            "weak_on": "Engineering detail — tell me what changed and whether it is significant, not how it works.",
        },
    },
    {
        "username": "business",
        "content": {
            "name": "Dan Foster",
            "describes_self_as": "Ops lead. I own the launch plan, budget and vendor commitments.",
            "expertise": ["program management", "budgeting", "vendor management"],
            "on_this_project": "Owns the hospital pilot launch date and the burn rate.",
            "cares_about": "Anything that moves a date or a cost. Everything else is noise.",
            "weak_on": "Both the engineering and the science — I need consequences, not mechanisms.",
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
