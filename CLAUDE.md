# Context Translator

---

## Problem Statement
How might AI help multi-disciplinary teams make sense of information, present ideas, align on decisions, and review work more effectively?

---

## Pitch

An n-way translator — not between languages, but between professional contexts. A project's ground truth lives in a neutral Intermediate Representation (IR). Every team member reads and writes that IR through a lens shaped by their own free-form context profile — whatever experience, expertise, and history they've chosen to describe. No fixed roles are baked into the system; "engineer," "biologist," "lawyer" are just example profile content for the demo.

---

## Core Pipeline

```
Natural language input (from a person with a context profile)
        ↓
Intermediate Representation (IR)   ← neutral, structured, source of truth
        ↓
Re-projected output (shaped by the reader's own context profile)
```

This is **re-projection, not translation**: output can surface implications the input didn't state directly (e.g. "this sensor change may require re-running your validation study"). That's the wow-factor and the hallucination risk — every inferred claim must trace back to a specific IR field. No ungrounded claims.

---

## Demo Scenario

**MedGuard** — a clinical device team. Four seeded context profiles: engineer, biologist, regulatory lawyer, business/ops lead.

1. Engineer posts: *"Bumped sampling rate to 2kHz, added debounce filter, should cut false positives."*
2. Parsed into IR: `{change: sensor sampling + filtering, affects: [validation protocol, FDA submission specs, timeline]}`
3. Biologist's view: flags need to re-run validation.
4. Lawyer's view: flags possible 510(k) supplement filing.
5. Business view: flags ~2 week timeline/cost impact.

Same fact, three different, non-obvious re-projections, each citing the IR field that triggered it.

---

## Tech Stack

- **Frontend:** React + shadcn, ESLint
- **Backend:** Python + Flask, Vulture
- **LLM:** Mistral

---

### 1. Foundation

**Backend**

- [X] IR entry, profile, and project schemas drafted
- [X] Backend repo scaffolded (Flask, Vulture)
- [ ] Storage layer for entries/projects/profiles (in-memory or file-based is fine for a 1-day build)
- [ ] Mistral client wrapper + API key wired via `.env`
- [ ] Seed script: create the MedGuard project and its four example profiles

**Frontend**

- [X] Frontend repo scaffolded (Vite + React + shadcn, ESLint)

---

### 2. Core Pipeline

**Backend**

- [ ] Extraction prompt: NL message → structured IR `content` JSON
- [ ] `POST /projects/:id/messages` — NL text + author → runs extraction, creates IR entry, appends id to `project.ir_entry_ids`
- [ ] Re-projection prompt: IR entry `content` + viewer's profile `content` → claim text + grounding path
- [ ] `GET /projects/:id/view?user_id=` — re-projects every entry in the project for that user's profile, returns claims
- [ ] `POST /profiles`, `GET /profiles/:id` — create/fetch a profile
- [ ] `POST /projects`, `GET /projects/:id` — create/fetch a project; creator is added to `users` and `admins`
- [ ] `GET /projects/:id/changes?since=` — entries with `created_at` after the given timestamp

**Frontend**

- [ ] API client wrapper for the endpoints above
- [ ] Project creation view

---

### 3. Wow-Factor

**Backend**

- [ ] Re-projection prompt explicitly asked to surface implications for the viewer, not just restate the fact
- [ ] Claims without a grounding path are dropped server-side, never returned as fact

**Frontend**

- [ ] Project feed listing IR entries
- [ ] Per-person view — pick a profile, fetch `/projects/:id/view` for it
- [ ] NL/IR toggle on entries and claims
- [ ] Grounding citation is clickable — expands/pops up the referenced IR entry
- [ ] "Since you last viewed" — last-viewed timestamp in localStorage per project, digest banner on load

---

### 4. Depth

**Backend**

- [ ] Meaning-preservation pass: prompt checks a claim against its source IR entry, flags drift/invention
- [ ] Amendment flow: extraction of the proposal + diff against existing entry `content` + apply-on-approval logic
- [ ] Amendment approval enforced server-side — only a user in `project.admins` can approve/reject, no exceptions
- [ ] `POST /projects/:id/promote` — an admin promotes another member to admin
- [ ] `POST /projects/:id/exit` — removes the caller from `users`/`admins`; if they were the last admin and other members remain, auto-promote one of them
- [ ] Version history: append-only log of `{entry_id, content, author, created_at}` written on every update
  - Potential recovery to old versions?

**Frontend**

- [ ] Amendment proposal UI + admin approval UI
- [ ] Admin management UI: promote a member, exit the project
- [ ] Version history view
- [ ] Attribution UI: show `author` on each entry/claim

---

### 5. Integration + Polish

**Backend**

- [ ] Atlassian API pulling one real data point into an IR entry
- [ ] Vulture clean

**Frontend**

- [ ] shadcn component pass for visual consistency
- [ ] Empty/loading states for feed, view, and changes digest
- [ ] ESLint clean

---

### 6. Demo Prep
- [ ] Full scripted MedGuard run-through, timed
- [ ] Backup plan (recording/screenshots) if live demo fails
- [ ] Deck finalized

---

### Future

- [ ] Conflict detection between contradictory statements
- [ ] Conflict resolution UX
- [ ] Evidence tracking for external sources
