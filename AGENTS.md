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
- [X] File-backed storage layer for entries/projects/profiles (`backend/storage.py`)
- [X] Mistral client wrapper + API key wired via `.env` (`backend/mistral_service.py`)
- [X] MedGuard seed: non-destructive startup ensure plus destructive clean-reset CLI for the project and four profiles

**Frontend**

- [X] Frontend repo scaffolded (Vite + React + shadcn, ESLint)

---

### 2. Auth

Real signup/login: username + password. Once logged in, the acting user is read from the session server-side — endpoints stop trusting a client-supplied user id for "who is doing this."

**Backend**

- [X] `POST /signup` — username + password → creates a `Profile` with empty `content` (password hashed, never returned by any endpoint)
- [X] `POST /login` / `POST /logout` — verifies password, starts/ends a session (Flask session cookie)
- [X] Auth check on protected routes — reject if no logged-in session; acting user = session's profile id, not a body/query param
- [X] `GET /profiles/:id` — fetch a profile (no password_hash in the response)
- [X] `PUT /profiles/me` — logged-in user edits their own `content` (self-description); editable any time, not just once

**Frontend**

- [X] Signup view — username + password only
- [X] Login view
- [X] Profile view — edit your own self-description (`Profile.content`) any time after logging in

---

### 3. Projects

**Backend**

- [X] `GET /projects` — projects the logged-in user is a member of (scan `users` lists; fine at demo scale)
- [X] `POST /projects`, `GET /projects/:id` — create/fetch a project; creator is added to `users` and `admins`
- [X] `POST /projects/:id/join` — adds the logged-in user to `users` (not `admins`)
- [X] Admin-managed add/remove member endpoints

**Frontend**

- [X] Home view — lists the projects you've joined; landing page after login, entry point into a project
- [X] Project creation view
- [X] Join-project view

---

### 4. Project View

The shell you land in after opening a project from the home view. Member management lives here — later milestones fill the same view with the IR feed and re-projected claims.

**Backend**

- [X] `POST /projects/:id/promote` — an admin promotes another member to admin
- [X] `POST /projects/:id/exit` — removes the logged-in user from `users`/`admins`; if they were the last admin and other members remain, auto-promote one of them

**Frontend**

- [X] Project view shell — project name, member list (username + whether they're an admin)
- [X] Promote button next to each member, visible only to admins
- [X] Add/remove member controls, visible only to admins
- [X] Exit-project button

---

### 5. Core Pipeline

**Backend**

- [X] Extraction prompt: NL message → structured IR `content` JSON
- [X] `POST /projects/:id/messages` — NL text (author = logged-in user) → runs extraction, creates IR entry, appends id to `project.ir`
- [X] Re-projection prompt: IR entry `content` + viewer's profile `content` → claim text + grounding path
- [X] `GET /projects/:id/view?user_id=` — re-projects every entry in the project for that user's profile, returns claims
- [X] `GET /projects/:id/changes?since=` — entries with `created_at` after the given timestamp
- [X] Multiple documents per project — each upload appends grounded entries to the same IR

**Frontend**

- [X] API client wrapper for the endpoints above
- [X] Multi-file project upload with automatic IR refresh

---

### 6. Wow-Factor

**Backend**

- [X] Re-projection prompt explicitly asked to surface implications for the viewer, not just restate the fact
- [X] Claims without a grounding path are dropped server-side, never returned as fact

**Frontend**

- [X] Project feed: chat-style timeline (time, author, content per row), not raw JSON — this is the "IR" side of the NL/IR toggle
- [X] Per-person view — pick a profile, fetch `/projects/:id/view` for it
- [X] Lens/IR/issues/raw workspace modes
- [X] Grounding citation is clickable — expands/pops up the referenced IR entry
- [X] "Since you last viewed" — last-viewed timestamp in localStorage per project, digest banner on load

---

### 7. Depth

**Backend**

- [X] Git-style issue workflow with collaborative solution branches
- [X] Append-only proposal revisions with contributor attribution and stale-base conflict checks
- [X] Independent assigned-expert review; contributors cannot self-approve
- [X] Approved solution closes the issue and becomes a grounded IR decision
- [X] Automatic post-change conflict review for messages, documents, and approved decisions
- [X] Model-detected issues require exact new/existing IR evidence and high confidence
- [X] Profile-aware participant/reviewer assignment with enforced reviewer independence
- [X] Duplicate automatic issues are suppressed by their cited IR evidence
- [ ] Meaning-preservation pass: prompt checks a claim against its source IR entry, flags drift/invention
- [ ] Amendment flow: extraction of the proposal + diff against existing entry `content` + apply-on-approval logic
- [ ] Amendment approval enforced server-side — only a user in `project.admins` can approve/reject, no exceptions
- [ ] Version history: append-only log of `{entry_id, content, author, created_at}` written on every update
  - Potential recovery to old versions?

**Frontend**

- [X] Issue, solution branch, revision, submit, approve, and reject UI
- [X] Automatic-conflict status, assignments, and collapsed source-evidence UI
- [ ] Amendment proposal UI + admin approval UI
- [ ] Version history view
- [X] Attribution UI: show `author` on each entry/claim

---

### 8. Integration + Polish

**Backend**

- [ ] Atlassian API pulling one real data point into an IR entry
- [X] Vulture clean

**Frontend**

- [ ] shadcn component pass for visual consistency
- [X] Empty/loading states for feed, view, and changes digest
- [X] Compact source-grouped project feed with details collapsed by default
- [X] ESLint clean

---

### 9. Demo Prep
- [ ] Full scripted MedGuard run-through, timed
- [ ] Backup plan (recording/screenshots) if live demo fails
- [ ] Deck finalized

---

### Future

- [ ] Conflict detection between contradictory statements
- [ ] Conflict resolution UX
- [ ] Evidence tracking for external sources
