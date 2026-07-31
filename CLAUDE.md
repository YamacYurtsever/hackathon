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

Storage was plain Python dicts in `store.py` — lost on every restart, painful mid-demo, and a blocker for version history. `store.py`'s functions were already the only way anything touched state, so swapping SQLite in behind them left the blueprints almost untouched.

**One thing changed for callers:** a returned dict is now a *copy*, so mutating it writes nothing. `profile["content"] = x` silently stopped working and became `store.update_profile_content(...)`, and `join`/`promote` had to re-read the project before returning it or the response was stale. If you find yourself editing a dict that came out of `store`, that's the bug.

- [X] SQLite via stdlib `sqlite3` — file-based, no server to run, survives restart
- [X] Tables for profiles, projects, project membership/admins, and IR entries
- [X] Keep `store.py`'s function signatures identical so blueprints and tests are untouched
- [X] Tests point at a temporary database file per test, replacing the dict-clearing fixture
- [X] Seed script becomes idempotent — don't re-seed MedGuard onto an existing database

The database lives at `backend/data.db` (gitignored); override with `DATABASE_PATH`. Delete the file to start clean — the seed reruns on next boot.

---

### 6. Core Pipeline

Pure backend — no UI yet. Exercised via the API client and curl. Prove the pipeline works before building the view on top of it.

**Backend**

- [X] Intent classification: is this input a statement of fact or a question? Cheap first pass, since the two paths diverge completely
- [X] `POST /projects/:id/input` — one endpoint behind the single input box. Returns either `{kind: "changeset", …}` (statement → proposed changes, **nothing stored**) or `{kind: "answer", …}` (question → grounded answer, nothing stored)
- [X] Accept an optional `kind` override on that endpoint, so the UI's "treat it as the other thing" doesn't need a second route
- [X] Extraction prompt: NL statement + existing project IR → a changeset of operations, `create` and/or `update` — one message can add a fact and revise an old one at once
- [X] `update` operations name the entry they revise and carry the new `content`, so the UI can diff old against new
- [X] Answer prompt: question + viewer's profile + project IR → grounded prose answer with sources
- [X] Re-projection prompt: IR entries + viewer's profile `content` → cohesive summary as `{text, source_entry_ids}` segments
- [X] Re-projection **filters**: entries irrelevant to the viewer are omitted entirely, not restated blandly. Choosing what to leave out is part of the job
- [X] Re-projection surfaces implications, including ones spanning several entries — not just a restatement of each fact
- [X] `GET /projects/:id/view` — re-projects the project for the logged-in user's profile, returns the segment array
- [X] `GET /projects/:id/changes?since=` — entries with `created_at` after the given timestamp

**Write path (the only way the IR changes)**

- [X] `POST /projects/:id/requests` — author confirms a changeset; stored as a pending request. This is the first point anything is persisted
- [X] `GET /projects/:id/requests` — pending requests for the project
- [X] `PUT /projects/:id/requests/:rid` — hand-edit a pending request's operations. Allowed for its author and for admins
- [X] An applied entry's `author` is the original proposer, never the admin who edited it — editing isn't authorship
- [X] Confirming always creates a request, even when the author is an admin — one path, and the approval step stays demoable
- [X] `POST /projects/:id/requests/:rid/approve` / `…/reject` — admin only, enforced server-side, no exceptions. Approving applies every operation in the changeset atomically
- [X] Rejecting deletes the request; a rejected proposal isn't a fact and doesn't belong in history
- [X] Reject an `update` whose target entry no longer exists rather than silently recreating it

**Grounding (verify in code, don't trust the prompt)**

- [X] Every claim carries its sources: which IR entries, and where in their `content`
- [X] A claim may cite **several** entries — a synthesis like "timeline slips ~2 weeks" can legitimately draw on three facts, and forcing a single source would misrepresent it
- [X] Resolve every cited path against the actual entry server-side; drop claims whose citations don't resolve. The model will happily invent a plausible-looking path, so this has to be a code check, not a prompt instruction

**Known gap this leaves.** Citation checking proves a segment *points* at real entries; it can't prove the text only says what those entries support. Live output already shows the difference — a summary cited two real entries and still slipped in "from the typical 1 kHz baseline for this device class", which no entry states. Closing that is the meaning-preservation pass in milestone 9, and until then the honest claim is "every claim is traceable", not "every claim is verified".

**Summary caching**

- [X] Cache the re-projected summary per (project, user) server-side — recomputing on every project open is slow and pointless when nothing changed
- [X] Cache key is a hash of (entry ids + their `created_at`) and the viewer's profile `content`, so both a new entry *and* an edited self-description bust it — no manual version counters
- [X] Server-side, not localStorage: only the server knows when either input changed, and a local cache would regenerate on every refresh or new browser
- [X] Q&A answers are deliberately **not** cached — every question differs, and a live call reads as "thinking", not "slow"

**Frontend**

- [X] API client wrapper for the endpoints above

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

**One input, not two.** Splitting "post a fact" from "ask a question" makes people classify their own thought before typing. There's a single box and the backend decides: a statement becomes a change to the IR, a question gets a grounded answer. *"Bumped sampling rate to 2kHz"* is a fact; *"does that affect my filing?"* is a question — you shouldn't have to tell us which.

Misclassification hurts in both directions, so it can't be silent: a fact swallowed as a question never gets recorded, and a question stored as a fact pollutes the IR. The UI always says which happened, and offers a one-click "no, treat it as the other thing".

### The write path: changeset → author confirms → admin approves

A statement doesn't become an entry directly. Extraction produces a **changeset** — one message can create a new entry *and* amend existing ones, and often does: *"actually we settled on 4kHz, and that pushes validation another week"* both revises a recorded fact and adds a new one. Then two gates before anything lands:

```
"bumped sampling to 4kHz,
 pushes validation a week"
        ↓  extraction
┌─────────────────────────────┐
│ Proposed changes            │   ← nothing stored yet
│ • UPDATE sampling_rate      │
│     2kHz → 4kHz             │
│ • NEW validation_window     │
│     +1 week                 │
│        [ NL │ IR ]          │   ← same toggle idea
│  [confirm] [edit] [discard] │
└─────────────────────────────┘
        ↓  author confirms
   pending request on the project
        ↓  admin approves
      applied to the IR
```

**Gate 1 — the author confirms.** Extraction is a guess at what someone meant, so they get to see it before anyone else does: *"here's what I understood."* Nothing is stored until they confirm, so an unconfirmed misread leaves no trace. This is also where the NL/IR toggle earns its keep a second time — read the change as plain language or as a raw diff of `content`.

**Gate 2 — an admin approves.** Confirmed changesets become pending requests on the project. Only an admin can apply them, and that's not optional. This is the one place the IR can be written, so it's the one place that needs a gate.

**Both gates allow hand-editing.** At gate 1 the author can correct our reading before submitting; at gate 2 an admin can fix a small error instead of rejecting and making someone retype. Editing means editing the raw `content` — so IR mode of the diff view is the editable one, which doubles as the escape hatch when extraction misfires during a live demo.

An edited request doesn't reassign authorship: the applied entry's `author` stays the original proposer. We deliberately don't track *who* edited it — that only pays off alongside persistent request history, which is a Depth item we may not reach. Add it then, not speculatively.

Settled:

- **Always queue.** Even when the author is an admin, their confirmation creates a request they then approve. One path instead of two, and the approval step is demoable without a second account.
- **No bounce-back.** An admin edit doesn't return to the author for re-confirmation; it applies on approval.

Same facts, two renderings. **Summary** is written for you and nobody else sees it in quite that form. **IR** is the neutral timeline everyone shares, identical for every member: time, author, and the structured fact itself. Flipping between them makes "the IR is the source of truth" something you can *see* rather than something we assert — and it's the natural demo moment: switch profiles, watch the summary change completely, flip to IR and it's byte-identical.

The IR side is still a readable timeline, not a JSON dump; an entry can expand to raw `content` for anyone who wants it.

---

### 7. Project View: Chat & Feed

The writing half — getting facts *into* the project and seeing them land. Builds the IR mode of the panel; the toggle itself arrives in 8, once there's a second mode to switch to.

**Frontend**

- [X] Single input box, always visible below the panel — posts to `/input`, shows a working state while Mistral runs
- [X] Result is never ambiguous: say whether the input was read as a fact or answered as a question, with a one-click "treat it as the other thing"
- [X] Feed: chat-style timeline, one row per IR entry — time, author username, the structured fact rendered readably
- [X] An entry expands to its raw `content` JSON for anyone who wants the unvarnished version
- [X] Feed refreshes after a change is applied, newest last (it reads as a conversation)
- [X] Empty state before the first message

**Frontend — confirmation (gate 1)**

- [X] Changeset preview after a statement: creates and updates listed together, updates shown as a diff of old vs new `content`
- [X] NL/IR toggle on the preview — read the change as plain language or as the raw diff
- [X] Confirm / edit / discard; discarding leaves nothing behind, since nothing was stored
- [X] Editing is hand-editing the raw `content` in IR mode — the escape hatch when extraction gets it wrong
- [X] Make it obvious this is *our reading* of what you said, not yet a fact

**Frontend — approval (gate 2)**

- [X] Pending-requests list on the project, visible to everyone (transparency), actionable only by admins
- [X] Approve / reject per request, with the same diff view the author confirmed
- [X] Admins can hand-edit a request before approving, in the same IR-mode editor the author used
- [X] Non-admins see their own requests are waiting, so nobody wonders why their fact never landed

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

The changeset/confirm/approve flow is no longer here — it became the core write path in 6 and 7.

- [ ] Meaning-preservation pass: prompt checks a summary segment against the entries it cites, flags drift/invention
- [ ] Version history: append-only log of `{entry_id, content, author, created_at}` written on every applied update
  - Potential recovery to old versions?

**Frontend**

- [ ] Version history view
- [ ] Attribution UI: show `author` on each entry
- [ ] Request history — who proposed what, who approved it, when

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
- [ ] Project change timeline view
