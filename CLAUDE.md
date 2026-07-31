# AGENTS.md — Context Translator

## Problem Statement
How might AI help multi-disciplinary teams make sense of information, present ideas, align on decisions, and review work more effectively?

## Pitch
An n-way translator — not between languages, but between professional contexts. A project's ground truth lives in a neutral Intermediate Representation (IR). Every team member reads and writes that IR through a lens shaped by their own free-form context profile — whatever experience, expertise, and history they've chosen to describe. No fixed roles are baked into the system; "engineer," "biologist," "lawyer" are just example profile content for the demo.

## Core Pipeline
```
Natural language input (from a person with a context profile)
        ↓
Intermediate Representation (IR)   ← neutral, structured, source of truth
        ↓
Re-projected output (shaped by the reader's own context profile)
```

This is **re-projection, not translation**: output can surface implications the input didn't state directly (e.g. "this sensor change may require re-running your validation study"). That's the wow-factor and the hallucination risk — every inferred claim must trace back to a specific IR field. No ungrounded claims.

## Demo Scenario
**MedGuard** — a clinical device team. Four seeded context profiles: engineer, biologist, regulatory lawyer, business/ops lead.

1. Engineer posts: *"Bumped sampling rate to 2kHz, added debounce filter, should cut false positives."*
2. Parsed into IR: `{change: sensor sampling + filtering, affects: [validation protocol, FDA submission specs, timeline]}`
3. Biologist's view: flags need to re-run validation.
4. Lawyer's view: flags possible 510(k) supplement filing.
5. Business view: flags ~2 week timeline/cost impact.

Same fact, three different, non-obvious re-projections, each citing the IR field that triggered it.

## Feature Backlog

**Must-have:**
- [ ] NL → IR extraction (Mistral)
- [ ] IR → context-specific re-projection (Mistral)
- [ ] Free-form context profile per user
- [ ] Cross-context effect propagation, computed at re-projection time
- [ ] Grounding: every claim cites its source IR field
- [ ] NL/IR toggle (summaries and amendments)
- [ ] "Since you last viewed" digest (local last-viewed timestamp → changes since then)
- [ ] Every IR change stored with timestamp + author

**Should-have:**
- [ ] Meaning-preservation check (second pass validates re-projection against IR)
- [ ] Amendment flow: NL proposal → IR diff → admin approval
- [ ] Version history view
- [ ] Attribution UI

**Stretch:**
- [ ] Conflict detection between contradictory statements
- [ ] Conflict resolution UX
- [ ] Ask-the-IR chat
- [ ] Evidence tracking for external sources
- [ ] One real integration (Atlassian API); other "connected apps" mocked

**Out of scope:** multiple real integrations, production-grade conflict resolution.

## Tech Stack
- **Frontend:** React + shadcn, ESLint
- **Backend:** Python + Flask, Vulture
- **LLM:** Mistral

## Milestones

### 1. Foundation
- [X] IR entry, profile, and project schemas drafted
- [X] Repo scaffolded

### 2. Core Pipeline
- [ ] NL → IR extraction working
- [ ] IR → context-specific re-projection working
- [ ] Full profile content (not just a role label) shapes output
- [ ] Flask endpoints: create project, post message, fetch re-projected view, fetch changes-since-timestamp

### 3. Wow-Factor
- [ ] Cross-context effect propagation working
- [ ] Grounding citations visible in UI
- [ ] Project feed + per-person view rendering
- [ ] NL/IR toggle on summary view
- [ ] "Since you last viewed" digest working

### 4. Depth (time-permitting)
- [ ] Meaning-preservation check
- [ ] Amendment + approval flow, with NL/IR toggle on the diff
- [ ] Version history view
- [ ] Attribution UI

### 5. Integration + Polish
- [ ] Atlassian API pulling one real data point into IR
- [ ] UI polish pass
- [ ] Lint/dead-code pass

### 6. Demo Prep
- [ ] Full scripted MedGuard run-through, timed
- [ ] Backup plan (recording/screenshots) if live demo fails
- [ ] Deck finalized

## Guardrails
- Every AI-generated claim must cite an IR field, or it doesn't get shown as fact.
- IR schema and pipeline first; validate against MedGuard once built.
- Query (read) path must be rock-solid. Amendment (write) path can be scripted/narrow for the demo.
