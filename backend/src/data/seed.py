from werkzeug.security import generate_password_hash

from . import store

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
            "description": (
                "Embedded firmware engineer, ten years in signal acquisition and "
                "mostly biopotential front-ends. I own the sensor front-end and the "
                "detection firmware on this project and I've been on it since kickoff. "
                "Talk to me in sampling rates, filter topologies and ADC behaviour — "
                "I don't need DSP or embedded work explained. What I do want to know "
                "is when something I changed lands on someone else's plate."
            ),
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
            "description": (
                "Clinical scientist. I design and run the validation studies that "
                "produce our performance claims, and on this project I own the "
                "false-positive characterisation study and the clinical evidence "
                "package. Study design, arrhythmia physiology and statistics are my "
                "own ground. Firmware and DSP are not — tell me what a signal chain "
                "change does to what I'm measuring, not how it works."
            ),
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
            "description": (
                "Regulatory counsel for medical devices, fifteen years of 510(k) and "
                "PMA submissions. I own the 510(k) here and joined about three months "
                "in. I know the framework and what triggers a new submission, so skip "
                "the primer. Skip the engineering detail too: tell me what changed and "
                "whether it's significant, and I'll work out what it means for the "
                "filing."
            ),
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
            "description": (
                "Ops lead. I own the launch plan, the budget and the vendor "
                "commitments, which on this project means the hospital pilot date and "
                "the burn rate. I'm not an engineer or a scientist and don't need to "
                "be — I need consequences, not mechanisms. If something moves a date "
                "or a cost, that's mine. If it doesn't, it's noise."
            ),
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

# How a real project starts: the creator describes it in a paragraph and
# approves what we read out of it. This is the message MedGuard was founded
# with — kept here so it's obvious where the entries below came from.
#
# The entries are written out literally rather than extracted by calling the
# model at boot: seeding has to be deterministic, offline, and not require an
# API key before the app will start. Re-running the paragraph through /input
# should produce something close to this list.
FOUNDING_MESSAGE = (
    "MedGuard is an implantable cardiac monitor that flags arrhythmia events "
    "for outpatient review. The biopotential front-end samples at 1 kHz with a "
    "second-order anti-aliasing filter. We're filing a 510(k) with the Reveal "
    "LINQ II as predicate. Detection runs on-device and its false-positive rate "
    "is the number the clinical evidence package lives or dies on, so Marcus is "
    "running a characterisation study against annotated Holter recordings. "
    "The hospital pilot is committed for 14 March and the programme budget is "
    "$2.4M through end of year."
)

# One fact per entry, neutral, no consequences worked out — the same shape
# reading the paragraph through the pipeline would produce.
#
# Note the sampling rate is 1 kHz. The demo's opening move is the engineer
# saying they bumped it to 2 kHz, which should land as an *update* to this
# entry with a visible before/after — not as another create.
FOUNDING_ENTRIES = [
    {
        "statement": "MedGuard is an implantable cardiac monitor that flags arrhythmia events for outpatient review.",
    },
    {
        "statement": "The biopotential front-end samples at 1 kHz.",
        "sampling_rate": "1 kHz",
    },
    {
        "statement": "The front-end uses a second-order anti-aliasing filter.",
    },
    {
        "statement": "The device is being filed as a 510(k) with the Reveal LINQ II as the predicate device.",
    },
    {
        "statement": "Arrhythmia detection runs on-device.",
    },
    {
        "statement": "The detection false-positive rate is the primary measure the clinical evidence package depends on.",
    },
    {
        "statement": "A false-positive characterisation study is being run against annotated Holter recordings.",
    },
    {
        "statement": "The hospital pilot is committed for 14 March.",
        "date": "14 March",
    },
    {
        "statement": "The programme budget is $2.4M through the end of the year.",
        "amount": "$2.4M",
    },
]


def seed_medguard() -> dict | None:
    """Creates the MedGuard demo project and its four profiles.

    Idempotent: the database now survives restarts, so re-seeding on every boot
    would pile up duplicate accounts. Returns None when it's already there.
    """
    existing = store.find_profile_by_username(EXAMPLE_PROFILES[0]["username"])
    if existing is not None:
        return None

    password_hash = generate_password_hash(SEED_PASSWORD)
    created_profiles = [
        store.create_profile(profile["username"], password_hash, profile["content"])
        for profile in EXAMPLE_PROFILES
    ]
    project = store.create_project("MedGuard", creator_id=created_profiles[0]["id"])
    for profile in created_profiles[1:]:
        store.add_member(project["id"], profile["id"])

    # Authored by the creator, since they're the one who wrote the founding
    # paragraph these were read out of.
    creator_id = created_profiles[0]["id"]
    for content in FOUNDING_ENTRIES:
        entry = store.create_entry(content, author=creator_id)
        store.add_entry_to_project(project["id"], entry["id"])

    return store.get_project(project["id"])


if __name__ == "__main__":
    import os

    store.init_db(os.environ.get("DATABASE_PATH"))
    seeded_project = seed_medguard()
    if seeded_project is None:
        print("MedGuard is already seeded — nothing to do.")
    else:
        print(
            f"Created project {seeded_project['id']!r} with users {seeded_project['users']}"
        )
