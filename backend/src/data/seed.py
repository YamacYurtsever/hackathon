from werkzeug.security import generate_password_hash

from . import store

# Content is free-form by design — these are just examples of what someone might
# write about themselves. It is one profile per person, not per project, so
# nothing here names a project or what they own in one: that's a fact about the
# project and belongs in its IR. Nothing in the pipeline reads a fixed "role" key. The
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
                "mostly biopotential front-ends. I work on sensor front-ends and "
                "detection firmware. Talk to me in sampling rates, filter topologies "
                "and ADC behaviour — I don't need DSP or embedded work explained. "
                "What I do want to know is when something I changed lands on someone "
                "else's plate."
            ),
            "describes_self_as": "Embedded firmware engineer. Ten years in signal acquisition, mostly biopotential front-ends.",
            "expertise": ["DSP", "ADC design", "firmware", "filter design"],
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
                "produce performance claims, and I own the clinical evidence behind "
                "them. Study design, cardiac physiology and statistics are my own "
                "ground. Firmware and DSP are not — tell me what a signal chain "
                "change does to what I'm measuring, not how it works."
            ),
            "describes_self_as": "Clinical scientist. I design and run the validation studies that produce our performance claims.",
            "expertise": ["study design", "cardiac physiology", "biostatistics"],
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
                "PMA submissions. I know the framework and what triggers a new "
                "submission, so skip the primer. Skip the engineering detail too: "
                "tell me what changed and whether it's significant, and I'll work out "
                "what it means for the filing."
            ),
            "describes_self_as": "Regulatory counsel, medical devices. Fifteen years of 510(k) and PMA submissions.",
            "expertise": ["FDA device regulation", "21 CFR", "submission strategy"],
            "assume_i_know": "The regulatory framework and what triggers a new submission.",
            "weak_on": "Engineering detail — tell me what changed and whether it is significant, not how it works.",
        },
    },
    {
        "username": "business",
        "content": {
            "name": "Dan Foster",
            "description": (
                "Ops lead. I own launch plans, budgets and vendor commitments — "
                "dates and burn rate. I'm not an engineer or a scientist and don't "
                "need to be: I need consequences, not mechanisms. If something moves "
                "a date or a cost, that's mine. If it doesn't, it's noise."
            ),
            "describes_self_as": "Ops lead. I own the launch plan, budget and vendor commitments.",
            "expertise": ["program management", "budgeting", "vendor management"],
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


# --- the other projects ---
#
# One project demos the pipeline; four demo the product. They differ in the
# things the UI actually keys off: who administers them, who can see them at
# all, and whether they currently have anything waiting or contradicting. Each
# seeded account lands on a different home page as a result.
#
# Facts are written out rather than extracted, for the same reason MedGuard's
# are: seeding has to be deterministic, offline, and free.

HALO_ENTRIES = [
    ("engineer", {"statement": "Halo is a large-volume infusion pump for inpatient use."}),
    ("engineer", {"statement": "The pump delivers between 0.1 and 999 mL/h."}),
    ("engineer", {"statement": "Occlusion detection triggers at 300 mmHg of downstream pressure."}),
    ("biologist", {"statement": "Flow accuracy is specified as ±5% across the full delivery range."}),
    ("business", {"statement": "IEC 60601-2-24 testing is booked with an external lab for 3 June."}),
    ("business", {"statement": "Two launch sites are committed for Q4."}),
    ("engineer", {"statement": "The pump firmware shares the detection stack used in MedGuard."}),
]

NORTHSTAR_ENTRIES = [
    ("business", {"statement": "NORTHSTAR is a multi-site observational study supporting the MedGuard filing."}),
    ("biologist", {"statement": "The enrolment target is 240 patients."}),
    ("biologist", {"statement": "Five sites are activated, with Massachusetts General as the coordinating centre."}),
    ("lawyer", {"statement": "IRB approval is in place at four of the five sites."}),
    ("business", {"statement": "The monitoring plan is risk-based, with quarterly site visits."}),
    ("business", {"statement": "Enrolment is committed to complete 300 patients before database lock."}),
]

AEGIS_ENTRIES = [
    ("lawyer", {"statement": "Aegis tracks post-market regulatory change affecting the device portfolio."}),
    ("lawyer", {"statement": "The EU MDR transition deadline for legacy devices is 31 December 2028."}),
    ("lawyer", {"statement": "FDA guidance on predetermined change control plans applies to AI-enabled devices."}),
    ("engineer", {"statement": "A change control plan must name the specific model versions it covers."}),
]

DEMO_PROJECTS = [
    {
        "name": "MedGuard",
        "admin": "engineer",
        "members": ["engineer", "biologist", "lawyer", "business"],
        # Every fact here came out of FOUNDING_MESSAGE above.
        "entries": [("engineer", content) for content in FOUNDING_ENTRIES],
    },
    {
        "name": "Halo Infusion Pump",
        # Administered by someone who didn't build it, which is the normal case
        # and the one where the merge gate earns its keep.
        "admin": "business",
        "members": ["engineer", "biologist", "business"],
        "entries": HALO_ENTRIES,
        # Waiting on the admin, so the queue isn't empty on a cold start.
        "pending": [
            (
                "engineer",
                "Dropping the occlusion threshold to 250 and pushing battery target to 8h",
                {"statement": "Occlusion detection triggers at 250 mmHg of downstream pressure."},
            ),
            (
                "engineer",
                "Dropping the occlusion threshold to 250 and pushing battery target to 8h",
                {"statement": "The battery runtime target is 8 hours."},
            ),
        ],
    },
    {
        "name": "NORTHSTAR Trial Ops",
        "admin": "biologist",
        "members": ["biologist", "lawyer", "business"],
        "entries": NORTHSTAR_ENTRIES,
        # Two people committed to different numbers, and neither was revising
        # the other — exactly the case the update path can't handle.
        "conflicts": [
            (
                1,
                5,
                "Enrolment cannot both target 240 patients and be committed to "
                "complete 300 before database lock.",
            )
        ],
    },
    {
        "name": "Aegis Regulatory Watch",
        "admin": "lawyer",
        "members": ["lawyer", "engineer"],
        "entries": AEGIS_ENTRIES,
    },
]


def seed_demo() -> dict | None:
    """Creates the demo accounts and their projects.

    Idempotent: the database survives restarts, so re-seeding on every boot
    would pile up duplicate accounts. Returns None when it's already there.
    """
    if store.find_profile_by_username(EXAMPLE_PROFILES[0]["username"]) is not None:
        return None

    password_hash = generate_password_hash(SEED_PASSWORD)
    people = {
        profile["username"]: store.create_profile(
            profile["username"], password_hash, profile["content"]
        )["id"]
        for profile in EXAMPLE_PROFILES
    }

    first = None
    for spec in DEMO_PROJECTS:
        project = store.create_project(spec["name"], creator_id=people[spec["admin"]])
        for username in spec["members"]:
            if username != spec["admin"]:
                store.add_member(project["id"], people[username])

        # Authorship is the point of the feed, so facts keep the person who
        # would have said them rather than all landing on the admin.
        entry_ids = []
        for username, content in spec["entries"]:
            entry = store.create_entry(content, author=people[username])
            store.add_entry_to_project(project["id"], entry["id"])
            entry_ids.append(entry["id"])

        for username, source_text, content in spec.get("pending", []):
            store.create_request(
                project["id"],
                people[username],
                source_text,
                {"op": "create", "content": content},
            )

        for a, b, reason in spec.get("conflicts", []):
            store.record_conflict(project["id"], entry_ids[a], entry_ids[b], reason)

        first = first or project

    return store.get_project(first["id"]) if first else None


if __name__ == "__main__":
    import os

    store.init_db(os.environ.get("DATABASE_PATH"))
    seeded_project = seed_demo()
    if seeded_project is None:
        print("Already seeded — nothing to do.")
    else:
        print(f"Seeded {len(DEMO_PROJECTS)} projects and {len(EXAMPLE_PROFILES)} accounts.")
