"""Run the extraction fixtures against a live Mistral model and print what came back.

Needs MISTRAL_API_KEY. The unit tests stay offline; this is the harness for
judging prompt quality, which no assertion can do for you.

    cd backend && source venv/bin/activate && python eval_extraction.py
    python eval_extraction.py canonical quote-trap   # a subset
"""

import json
import os
import sys

sys.path.insert(0, "src")

from dotenv import load_dotenv  # noqa: E402

from extraction.extract import extract_changeset  # noqa: E402
from extraction.fixtures import FIXTURES  # noqa: E402

load_dotenv()

# Stands in for a project that already knows the sampling rate, so the revision
# fixture has something to update.
EXISTING = [
    {
        "id": "e-17",
        "content": {
            "statement": "The ECG sensor sampling rate is 2 kHz.",
            "subject": "ECG sensor sampling rate",
            "source_quote": "sampling rate to 2kHz",
            "certainty": "stated",
            "current": {"value": 2000, "unit": "Hz"},
        },
    }
]


def run(fixture: dict) -> bool:
    print(f"\n{'=' * 70}\n{fixture['label']}  [{fixture['id']}]\n{'=' * 70}")
    print(f"input: {fixture['text']}\n")

    existing = EXISTING if fixture.get("needs_existing") else []
    result = extract_changeset(fixture["text"], existing=existing)

    for operation in result["operations"]:
        target = f" -> {operation['target_id']}" if operation.get("target_id") else ""
        print(f"  [{operation['op']}{target}] {json.dumps(operation['content'], indent=4)}")

    for item in result["unresolved"]:
        print(f"  ? {item['quote']!r}: {item['issue']}")

    for item in result["rejected"]:
        print(f"  ✗ REJECTED: {'; '.join(item['problems'])}")

    # Search the whole content object, not just "statement": a figure captured
    # as {"value": 4.2, "unit": "%"} is a better extraction than one buried in
    # prose, and shouldn't read as a miss.
    extracted = json.dumps([op["content"] for op in result["operations"]]).lower()
    missing = [word for word in fixture["mentions"] if word.lower() not in extracted]

    checks = {
        f"≥{fixture['min_operations']} operations": len(result["operations"])
        >= fixture["min_operations"],
        "all expected topics mentioned": not missing,
        "nothing rejected": not result["rejected"],
    }
    if fixture["expect_unresolved"]:
        checks["flagged something unresolved"] = bool(result["unresolved"])

    print()
    for label, ok in checks.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    if missing:
        print(f"        missing topics: {missing}")
    print(f"  note: {fixture['note']}")
    print(
        f"  {result['diagnostics']['attempts']} attempt(s), "
        f"{result['diagnostics']['latency_ms']}ms"
    )

    return all(checks.values())


def main() -> int:
    if not os.environ.get("MISTRAL_API_KEY"):
        print("MISTRAL_API_KEY is not set. Put it in backend/.env (see .env.example).")
        return 1

    wanted = set(sys.argv[1:])
    selected = [f for f in FIXTURES if not wanted or f["id"] in wanted]
    if not selected:
        print(f"No fixtures matched. Available: {', '.join(f['id'] for f in FIXTURES)}")
        return 1

    results = {fixture["id"]: run(fixture) for fixture in selected}

    passed = sum(results.values())
    print(f"\n{'=' * 70}\n{passed}/{len(results)} fixtures passed every check")
    for fixture_id, ok in results.items():
        if not ok:
            print(f"  needs a look: {fixture_id}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
