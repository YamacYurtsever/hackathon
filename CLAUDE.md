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
- **Backend:** Python + Flask, SQLite, Vulture, pytest
- **LLM:** Mistral

Run the backend tests with `cd backend && pytest`. Keep endpoint behaviour covered there — especially auth and permission rules, where a regression is a privilege-escalation bug rather than a visible glitch.

---

### 1. Foundation

**Backend**

- [X] IR entry, profile, and project schemas drafted
- [X] Backend repo scaffolded (Flask, Vulture)
- [X] Storage layer for entries/projects/profiles (in-memory, `backend/store.py`)
- [X] Mistral client wrapper + API key wired via `.env` (`backend/mistral_client.py`)
- [X] Seed script: create the MedGuard project and its four example profiles (`backend/seed.py`, wired into app startup)

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

Projects are not browsable — you only ever see projects you're a member of. Joining happens through an invite link an admin shares. The project id doubles as the invite token: it's a UUID4, so it can't be guessed, only shared.

**Backend**

- [X] `GET /projects` — projects the logged-in user is a member of (scan `users` lists; fine at demo scale)
- [X] `POST /projects`, `GET /projects/:id` — create/fetch a project; creator is added to `users` and `admins`
- [X] `GET /projects/:id/invite` — name-only preview so an invitee can see what they're joining; no members or IR content until they join
- [X] `POST /projects/:id/join` — adds the logged-in user to `users` (not `admins`)

**Frontend**

- [X] Home view — lists the projects you've joined; landing page after login, entry point into a project
- [X] Project creation view
- [X] Invite landing page (`/invite/:projectId`) — shows the project name and a join button

---

### 4. Project View Shell

The shell you land in after opening a project from the home view. Member management lives here; milestones 7 and 8 fill the same screen with the feed, composer, and re-projected summary.

**Backend**

- [X] `GET /projects/:id/members` — member profiles with admin flags, so the UI shows names not ids
- [X] `POST /projects/:id/promote` — an admin promotes another member to admin
- [X] `POST /projects/:id/exit` — removes the logged-in user from `users`/`admins`; if they were the last admin and other members remain, auto-promote one of them; if they were the last member, delete the project (an empty project could never regain an admin)

**Frontend**

- [X] Project view shell — project name, member list (username + whether they're an admin)
- [X] Promote button next to each member, visible only to admins
- [X] Copy-invite-link button, visible only to admins
- [X] Exit-project button

---

### 5. Persistence

Storage is currently plain Python dicts in `store.py` — everything is lost on restart, which is painful mid-demo and blocks version history. `store.py`'s functions are already the only way anything touches state, so they're a clean seam: swap the implementation behind them and nothing else changes.

- [ ] SQLite via stdlib `sqlite3` — file-based, no server to run, survives restart
- [ ] Tables for profiles, projects, project membership/admins, and IR entries
- [ ] Keep `store.py`'s function signatures identical so blueprints and tests are untouched
- [ ] Tests point at a temporary database file per test, replacing the dict-clearing fixture
- [ ] Seed script becomes idempotent — don't re-seed MedGuard onto an existing database

*If time is short:* dumping the existing dicts to a JSON file on write and loading on boot buys persistence in a fraction of the time. Worse for concurrent writes and version history, fine for a demo.

---

### 6. Core Pipeline

Pure backend — no UI yet. Exercised via the API client and curl. Prove the pipeline works before building the view on top of it.

**Backend**

- [ ] Intent classification: is this input a statement of fact or a question? Cheap first pass, since the two paths diverge completely
- [ ] `POST /projects/:id/input` — one endpoint behind the single input box. Returns either `{kind: "entry", …}` (statement → extracted, stored) or `{kind: "answer", …}` (question → grounded answer, nothing stored)
- [ ] Accept an optional `kind` override on that endpoint, so the UI's "treat it as the other thing" doesn't need a second route
- [ ] Extraction prompt: NL statement → structured IR `content` JSON; creates the entry and appends its id to `project.ir`
- [ ] Answer prompt: question + viewer's profile + project IR → grounded prose answer with sources
- [ ] Re-projection prompt: IR entries + viewer's profile `content` → cohesive summary as `{text, source_entry_ids}` segments
- [ ] Re-projection **filters**: entries irrelevant to the viewer are omitted entirely, not restated blandly. Choosing what to leave out is part of the job
- [ ] Re-projection surfaces implications, including ones spanning several entries — not just a restatement of each fact
- [ ] `GET /projects/:id/view` — re-projects the project for the logged-in user's profile, returns the segment array
- [ ] `GET /projects/:id/changes?since=` — entries with `created_at` after the given timestamp

**Grounding (verify in code, don't trust the prompt)**

- [ ] Every claim carries its sources: which IR entries, and where in their `content`
- [ ] A claim may cite **several** entries — a synthesis like "timeline slips ~2 weeks" can legitimately draw on three facts, and forcing a single source would misrepresent it
- [ ] Resolve every cited path against the actual entry server-side; drop claims whose citations don't resolve. The model will happily invent a plausible-looking path, so this has to be a code check, not a prompt instruction

**Summary caching**

- [ ] Cache the re-projected summary per (project, user) server-side — recomputing on every project open is slow and pointless when nothing changed
- [ ] Cache key is a hash of (entry ids + their `created_at`) and the viewer's profile `content`, so both a new entry *and* an edited self-description bust it — no manual version counters
- [ ] Server-side, not localStorage: only the server knows when either input changed, and a local cache would regenerate on every refresh or new browser
- [ ] Q&A answers are deliberately **not** cached — every question differs, and a live call reads as "thinking", not "slow"

**Frontend**

- [ ] API client wrapper for the endpoints above

---

## The Project View

Milestones 7 and 8 build one screen — the app's centrepiece and the hardest part. Everything else exists to make this view possible, so it's split into "writing" and "reading" halves rather than built in one go.

**One toggle, two modes of the same panel.** Summary and thread are not stacked — the toggle swaps which one you're looking at. Everything around it (header, digest, input box) stays put.

```
Summary — cohesive prose, for you     IR — the complete record
┌────────────────────────────────┐    ┌────────────────────────────────┐
│ MedGuard        [invite][leave]│    │ MedGuard        [invite][leave]│
├────────────────────────────────┤    ├────────────────────────────────┤
│ Since you last viewed: 3 ⌄     │← 8 │ Since you last viewed: 3 ⌄     │
├────────────────────────────────┤    ├────────────────────────────────┤
│              [ Summary │ IR ]  │← 8 │              [ Summary │ IR ]  │
│                                │    │                                │
│ The sensor spec changed this   │    │ 09:14 engineer                 │
│ week — sampling is now 2kHz    │    │   sampling_rate: 1kHz → 2kHz   │
│ with a debounce filter [1].    │    │   filter: debounce added       │
│ That's a change to a spec'd    │    │ 09:20 biologist                │
│ parameter, so it likely needs  │    │   validation_window: +2 weeks  │
│ a 510(k) supplement. Combined  │    │ 09:31 biologist                │
│ with the validation re-run [2],│    │   assay_protocol: buffer swap  │
│ your filing date moves ~2      │    │ 09:44 business                 │
│ weeks.                         │    │   budget_q3: approved          │
│                    ⌄ sources   │    │                                │
├────────────────────────────────┤    ├────────────────────────────────┤
│ [ say something, or ask…  ][→] │← 7 │ [ say something, or ask…  ][→] │← 7
└────────────────────────────────┘    └────────────────────────────────┘
```

**Summary is prose, not rows — and it filters.** Not every fact matters to every reader: the assay buffer swap above is real, recorded, and visible in IR, but it never appears in the lawyer's summary because it doesn't touch their filing. Deciding what's *relevant* to you is as much a part of re-projection as deciding how to word it. So the two sides deliberately don't line up row-for-row — IR is the complete record, summary is your reading of it, and it may legitimately skip most of it.

**How prose stays grounded.** Re-projection returns the summary as an array of `{text, source_entry_ids}` segments, which the UI concatenates into flowing paragraphs. The reader sees continuous prose with unobtrusive `[1]`-style markers; the server still verifies that every segment resolves to real entries and drops the ones that don't. Cohesive to read, still fully traceable — we don't have to choose.

**The toggle is prose ↔ its evidence.** Because the summary carries the ids of every entry it drew on, flipping to IR isn't switching to an unrelated screen — it's showing the receipts for what you just read. Those referenced entries are what IR mode displays, in order, so "where did that claim come from?" is one click, not a hunt. A "show everything" control expands to the project's full record for anyone who wants the entries their summary left out.

This is the demo in one gesture: read a paragraph written for you, flip, and see the neutral facts it was built from — then switch profiles and watch the prose change while those facts don't.

**One input, not two.** Splitting "post a fact" from "ask a question" makes people classify their own thought before typing. There's a single box and the backend decides: a statement becomes an IR entry, a question gets a grounded answer. *"Bumped sampling rate to 2kHz"* is a fact; *"does that affect my filing?"* is a question — you shouldn't have to tell us which.

Misclassification hurts in both directions, so it can't be silent: a fact swallowed as a question never gets recorded, and a question stored as a fact pollutes the IR. The UI always says which happened, and offers a one-click "no, treat it as the other thing".

Same facts, two renderings. **Summary** is written for you and nobody else sees it in quite that form. **IR** is the neutral timeline everyone shares, identical for every member: time, author, and the structured fact itself. Flipping between them makes "the IR is the source of truth" something you can *see* rather than something we assert — and it's the natural demo moment: switch profiles, watch the summary change completely, flip to IR and it's byte-identical.

The IR side is still a readable timeline, not a JSON dump; an entry can expand to raw `content` for anyone who wants it.

---

### 7. Project View: Chat & Feed

The writing half — getting facts *into* the project and seeing them land. Builds the IR mode of the panel; the toggle itself arrives in 8, once there's a second mode to switch to.

**Frontend**

- [ ] Single input box, always visible below the panel — posts to `/input`, shows a working state while Mistral runs
- [ ] Result is never ambiguous: say whether the input was recorded as a fact or answered as a question, with a one-click "treat it as the other thing"
- [ ] Feed: chat-style timeline, one row per IR entry — time, author username, the structured fact rendered readably
- [ ] An entry expands to its raw `content` JSON for anyone who wants the unvarnished version
- [ ] Feed refreshes after posting, newest last (it reads as a conversation)
- [ ] Empty state before the first message

---

### 8. Project View: Summary & Digest

The reading half — the same facts, re-projected through *your* context, plus asking your own questions of them. This is the demo's payload.

**Frontend — summary and the toggle**

- [ ] Summary mode — segments from `/view` concatenated into flowing paragraphs, not a bulleted list of rows
- [ ] Single `[ Summary | IR ]` toggle swapping the main panel between summary and thread — not two panels stacked, and not a toggle per panel
- [ ] Toggle choice persists per project (localStorage), so the demo doesn't reset it on every navigation
- [ ] Switching profiles visibly changes the summary while the IR side stays identical — the whole pitch in one interaction, so make it easy to demo

**Frontend — citations (present, not loud)**

- [ ] Unobtrusive `[1]`-style markers at segment boundaries, not a footnote on every sentence
- [ ] IR mode shows the entries the summary cited, in order — the toggle is prose ↔ its evidence, not two unrelated screens
- [ ] Clicking a marker flips to IR with that entry highlighted, so "where did that come from?" is one click
- [ ] "Show everything" control in IR mode reveals the project's full record, including entries the summary filtered out

**Frontend — answers**

- [ ] Answers from `/input` render in the panel with their sources, re-projected through the asker's profile like the summary
- [ ] Answers are transient — they aren't facts, so they never enter the feed or the IR
- [ ] Loading state while it thinks; this call is never cached, so it's always a live round-trip

**Frontend — digest**

- [ ] "Since you last viewed" — last-viewed timestamp per project in localStorage, `GET /changes?since=`, digest banner on open
- [ ] Digest dismisses and updates the stored timestamp
- [ ] No banner when nothing changed (the cached summary is served as-is)

---

### 9. Depth

**Backend**

- [ ] Meaning-preservation pass: prompt checks a claim against its source IR entry, flags drift/invention
- [ ] Amendment flow: extraction of the proposal + diff against existing entry `content` + apply-on-approval logic
- [ ] Amendment approval enforced server-side — only a user in `project.admins` can approve/reject, no exceptions
- [ ] Version history: append-only log of `{entry_id, content, author, created_at}` written on every update
  - Potential recovery to old versions?

**Frontend**

- [ ] Amendment proposal UI + admin approval UI
- [ ] Version history view
- [ ] Attribution UI: show `author` on each entry/claim

---

### 10. Integration + Polish

**Backend**

- [ ] Atlassian API pulling one real data point into an IR entry
- [ ] Vulture clean

**Frontend**

- [ ] shadcn component pass for visual consistency
- [ ] Empty/loading states for feed, view, and changes digest
- [ ] ESLint clean

---

### 11. Demo Prep
- [ ] Full scripted MedGuard run-through, timed
- [ ] Backup plan (recording/screenshots) if live demo fails
- [ ] Deck finalized

---

### Future

- [ ] Conflict detection between contradictory statements
- [ ] Conflict resolution UX
- [ ] Evidence tracking for external sources
