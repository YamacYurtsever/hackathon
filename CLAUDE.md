# Contextor

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
- [X] Seed MedGuard the way a real project starts — a founding paragraph from the creator, and the nine facts read out of it. The paragraph stays in `seed.py` so it's obvious where the entries came from; the entries are written out literally rather than extracted at boot, since seeding has to be deterministic, offline, and not need an API key before the app will start
- [X] The seeded sampling rate is **1 kHz**, not 2 kHz. The demo's opening move — "bumped sampling to 2kHz" — then lands as an *update* with a visible before/after, instead of yet another create. The update path was previously not demoable at all

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

- [X] `POST /projects/:id/input` — one endpoint behind the single input box. Returns `{operations, answer, dropped}` and stores **nothing**. No classifier: one call handles a statement, a question, or both at once
- [X] Interpretation prompt: NL message + existing project IR → operations (`create` and/or `update`) plus an answer — one message can add a fact, revise an old one, and ask something
- [X] `update` operations name the entry they revise and carry the new `content`, so the UI can diff old against new
- [X] Re-projection prompt: IR entries + viewer's profile `content` → cohesive summary as `{text, source_entry_ids}` segments
- [X] Re-projection **filters**: entries irrelevant to the viewer are omitted entirely, not restated blandly. Choosing what to leave out is part of the job
- [X] Re-projection surfaces implications, including ones spanning several entries — not just a restatement of each fact
- [X] `GET /projects/:id/view` — re-projects the project for the logged-in user's profile, returns the segment array
- [X] `GET /projects/:id/changes?since=` — entries with `created_at` after the given timestamp

**Write path (the only way the IR changes)**

- [X] `POST /projects/:id/requests` — author submits proposed changes for review; **each becomes its own request**, so an admin can merge one and reject another instead of being handed a bundle to take or leave. First point anything is persisted
- [X] `GET /projects/:id/requests` — pending requests for the project
- [X] `PUT /projects/:id/requests/:rid` — hand-edit a pending request's operation. Allowed for its author and for admins
- [X] A merged entry's `author` is the original proposer, never the admin who merged or edited it — neither is authorship
- [X] Submitting always creates a request. An admin's own request is then merged in the same call, so there is still exactly one path into the IR — create-then-merge — and authorship is assigned exactly as it is for anyone else
- [X] `POST /projects/:id/requests/:rid/merge` / `…/reject` — admin only, enforced server-side, no exceptions. Merging is the only write to the IR, and one request carries one change, so there's nothing to apply partially
- [X] Rejecting deletes the request; a rejected proposal isn't a fact and doesn't belong in history
- [X] Reject an `update` whose target entry no longer exists rather than silently recreating it

**Grounding (verify in code, don't trust the prompt)**

- [X] Every summary segment carries its sources: the IR entries it drew on
- [X] A claim may cite **several** entries — a synthesis like "timeline slips ~2 weeks" can legitimately draw on three facts, and forcing a single source would misrepresent it
- [X] Resolve every cited id against the project's actual entries server-side; drop segments whose citations don't resolve. The model will happily cite an id that doesn't exist, so this has to be a code check, not a prompt instruction
- [X] Strip entry ids out of the prose itself. Ids belong in `source_entry_ids`, but the model kept inlining them too — "the false-positive rate (ada04be8-f58c-…) now underpins the 510(k)" — which is unreadable and was visible in three separate live summaries. Same principle as the citation check: fixed in code, not asked for in the prompt

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

**One toggle, two modes of the same panel.** NL and thread are not stacked — the toggle swaps which one you're looking at. Everything around it (header, digest, input box) stays put.

```
NL — cohesive prose, for you          IR — the complete record
┌────────────────────────────────┐    ┌────────────────────────────────┐
│ MedGuard        [invite][leave]│    │ MedGuard        [invite][leave]│
├────────────────────────────────┤    ├────────────────────────────────┤
│ Since you last viewed: 3 ⌄     │← 8 │ Since you last viewed: 3 ⌄     │
├────────────────────────────────┤    ├────────────────────────────────┤
│              [ NL │ IR ]       │← 8 │              [ NL │ IR ]       │
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

**NL is prose, not rows — and it filters.** Not every fact matters to every reader: the assay buffer swap above is real, recorded, and visible in IR, but it never appears in the lawyer's summary because it doesn't touch their filing. Deciding what's *relevant* to you is as much a part of re-projection as deciding how to word it. So the two sides deliberately don't line up row-for-row — IR is the complete record, summary is your reading of it, and it may legitimately skip most of it.

**How prose stays grounded.** Re-projection returns the summary as an array of `{text, source_entry_ids}` segments, which the UI concatenates into flowing paragraphs. The reader sees continuous prose with unobtrusive `[1]`-style markers; the server still verifies that every segment resolves to real entries and drops the ones that don't. Cohesive to read, still fully traceable — we don't have to choose.

**Cite, don't recite.** A citation points at wording, which is precisely why the prose doesn't have to reproduce it. A segment that reads like its entry with the edges smoothed off has spent the reader's attention and told them nothing they couldn't get from IR — and IR is one click away, rendered for exactly that. So re-projection is required to *interpret*: what this means for you, what follows from it, what it costs you. The marker carries the reader back to the verbatim fact if they want it.

The line this must not cross: interpreting a fact is the job, altering it isn't. Figures, dates and names survive interpretation exactly — "2 kHz" never becomes "a higher rate". Loose paraphrase is a correctness bug wearing prose.

**The toggle is prose ↔ its evidence.** Because the prose carries the ids of every entry it drew on, flipping to IR isn't switching to an unrelated screen — it's showing the receipts for what you just read. IR displays exactly those referenced entries, ordered by citation number so `[1]` is first and following a marker lands where you expect. There's no "show everything" escape hatch: IR is the evidence for what the panel is currently showing, and a button to make it something else only muddles that. When nothing is cited yet the whole record shows, in time order, since there's no reading for it to be evidence *for*.

This is the demo in one gesture: read a paragraph written for you, flip, and see the neutral facts it was built from — then switch profiles and watch the prose change while those facts don't.

**One input, not two.** Splitting "post a fact" from "ask a question" makes people classify their own thought before typing. There's a single box, and one call reads the message for both: proposed changes to the IR, and an answer if it asked something.

Crucially it can be *both*. *"We settled on 4kHz — does that change what we file?"* is a fact and a question at once; a classifier picking one would silently lose the other half. Nothing is classified, so nothing is misclassified.

### The write path: proposed → submitted → merged

A statement doesn't become an entry directly. Reading a message produces **proposed changes** — one message can create a new entry *and* amend existing ones, and often does: *"actually we settled on 4kHz, and that pushes validation another week"* both revises a recorded fact and adds a new one. Each proposal is reviewed on its own, then passes two gates before it lands:

```
"bumped sampling to 4kHz,
 pushes validation a week"
        ↓  read as proposals
┌─────────────────────────────┐
│ Here's what we understood   │   ← nothing stored yet
│ ┌─────────────────────────┐ │
│ │ revises an existing fact│ │
│ │ ~~2kHz~~ → 4kHz         │ │
│ │      [edit] [drop]      │ │
│ ├─────────────────────────┤ │
│ │ new fact                │ │
│ │ validation +1 week      │ │
│ │      [edit] [drop]      │ │
│ └─────────────────────────┘ │
│   [ submit 2 for review ]   │
└─────────────────────────────┘
        ↓  author submits
  one pending request per change
        ↓  admin merges each
        merged into the IR
```

Three distinct acts, three distinct words — reusing "approve" for two of them hides the fact that the author's decision doesn't put anything in the IR:

- **proposed** — what reading the message produced. Not stored.
- **submitted** — the author sent it for review. Stored as a pending request, still not a fact.
- **merged** — an admin applied it. Now it's in the IR.

**Gate 1 — the author submits.** Our reading is a guess at what someone meant, so they see it before anyone else does: *"here's what we understood."* Each proposal is kept, edited, or dropped on its own — a message often says several things and you shouldn't have to take them as a bundle. Nothing is stored until they submit, so a misread they discard leaves no trace. Submitting is *not* approving: it only queues the change for review.

**Gate 2 — an admin merges.** Each submitted change becomes its own pending request. Only an admin can merge one, and that's not optional. This is the one place the IR can be written, so it's the one place that needs a gate — and because a request carries a single change, an admin can merge one and reject another rather than being handed all-or-nothing.

**Both gates allow hand-editing.** At gate 1 the author can correct our reading before submitting; at gate 2 an admin can fix a small error instead of rejecting and making someone retype. Editing means editing the raw `content`, which doubles as the escape hatch when the model misfires during a live demo.

An edited request doesn't reassign authorship: the applied entry's `author` stays the original proposer. We deliberately don't track *who* edited it — that only pays off alongside persistent request history, which is a Depth item we may not reach. Add it then, not speculatively.

Settled:

- **An admin's own changes land on confirm.** Gate 1 asks the author "is this what you meant?"; gate 2 asks an admin "should this be in the project?". When those are the same person, gate 2 is a dialog with one possible answer, and making them click it teaches them to click merge without reading. So an admin's submission is merged in the same request — still via create-then-merge, so the IR has one write path and authorship is unchanged. Everyone else's still waits.

  (This reverses an earlier decision to always queue, which was made to keep the merge step demoable without a second account. The seeded profiles give us that account, so the demo no longer needs the friction.)
- **No bounce-back.** An admin edit doesn't return to the author for re-confirmation; it lands on merge.

Same facts, two renderings. **NL** — the natural-language reading — is written for you and nobody else sees it in quite that form. **IR** is the neutral timeline everyone shares, identical for every member: time, author, and the structured fact itself. Flipping between them makes "the IR is the source of truth" something you can *see* rather than something we assert — and it's the natural demo moment: switch profiles, watch the summary change completely, flip to IR and it's byte-identical.

The IR side is a readable timeline, not a JSON dump: an entry shows its time, its author, and its statement, and nothing else. The raw-`content` expander and the subject tags were both removed — they were debug affordances that made the neutral record look like a database console, which is the opposite of the point.

---

### 7. Project View: Chat & Feed

The writing half — getting facts *into* the project and seeing them land. Builds the IR mode of the panel; the toggle itself arrives in 8, once there's a second mode to switch to.

**Frontend**

- [X] Single input box, always visible below the panel — posts to `/input`, shows a working state while Mistral runs
- [X] Result is never ambiguous: proposed changes and any answer both shown, and a count of anything the server had to discard rather than losing it silently
- [X] Feed: chat-style timeline, one row per IR entry — time, author username, the structured fact rendered readably
- [X] An entry shows time, author and statement — nothing else. No raw-JSON expander, no subject tags
- [X] Feed refreshes after a change is merged, newest last (it reads as a conversation)
- [X] Empty state before the first message

**Frontend — submission (gate 1)**

- [X] Each proposed change previewed on its own — keep, edit, or drop individually before sending; updates shown as a diff of old vs new `content`
- [X] Each change reads as plain language, with Edit revealing the raw `content` to fix by hand
- [X] Keep / edit / drop each one; discarding leaves nothing behind, since nothing was stored
- [X] Hand-editing is the escape hatch when the model gets it wrong
- [X] Make it obvious this is *our reading* of what you said, not yet a fact

**Frontend — merging (gate 2)**

- [X] Pending-requests queue behind a header button, visible to everyone (transparency), actionable only by admins
- [X] Merge / reject per request, with the same view the author submitted
- [X] Admins can hand-edit a request before merging, in the same editor the author used
- [X] "Merge all N" for admins when more than one is queued. Founding a project is one paragraph that yields ~10 facts, and merging them one at a time is ten clicks for a decision you already made in one. Per-request merge/reject stays for when you do want to go fact by fact; a failure in the batch skips that request and leaves it queued rather than aborting the rest
- [X] Non-admins see their own submissions are waiting, so nobody wonders why their fact never landed

---

### 8. Project View: NL & Digest

The reading half — the same facts, re-projected through *your* context, plus asking your own questions of them. This is the demo's payload.

**Frontend — summary and the toggle**

- [X] NL mode — segments from `/view` concatenated into flowing paragraphs, not a bulleted list of rows
- [X] Single `[ NL | IR ]` toggle swapping the main panel between the natural-language reading and the thread — not two panels stacked, and not a toggle per panel
- [X] Toggle choice persists per project (localStorage), so the demo doesn't reset it on every navigation
- [X] Switching profiles visibly changes the summary while the IR side stays identical — the whole pitch in one interaction, so make it easy to demo

**Frontend — citations (present, not loud)**

- [X] Unobtrusive `[1]`-style markers at segment boundaries, not a footnote on every sentence
- [X] IR mode shows the entries the panel cited — the summary's, or an answer's while one stands — ordered by citation number rather than by time
- [X] Clicking a marker flips to IR with that entry highlighted, so "where did that come from?" is one click
- [X] No "show everything" control. IR is the evidence for what you're reading; the full record shows only when nothing is cited yet

**Frontend — answers**

- [X] Answers from `/input` render in the panel with their sources, re-projected through the asker's profile like the summary. Reading the message decides *whether* something was asked; `reprojection.answer` then answers it, so an answer gets the same citation check the summary does
- [X] **An answer may reason; a summary may not.** A summary states what the project is, so an uncited segment there is an unsourced claim and is dropped. An answer to "who do you think this product is for?" has no recorded answer, and inferring one from the entries is the useful reply — so uncited segments survive in answers. They carry no `[n]` marker, and that absence is what tells the reader it's inference rather than record. The line is asserting a fact the entries don't contain, not having an opinion
- [X] Answers are transient — they aren't facts, so they never enter the feed or the IR
- [X] The answer renders **inside** the summary panel, replacing it until dismissed — not in a second card below it. One panel, one thing to read; asking a question swaps what the panel is showing, and "Back to summary" swaps it back. Asking while in IR mode flips you to summary, or the answer would land off-screen
- [X] Loading state while it thinks; this call is never cached, so it's always a live round-trip

**Frontend — digest**

- [X] "Since you last viewed" — last-viewed timestamp per project in localStorage, `GET /changes?since=`
- [X] Digest dismisses and updates the stored timestamp
- [X] No button when nothing changed (the cached summary is served as-is)
- [X] Changes you merged yourself never count as new. "Since you last looked" means what you haven't seen, and you have very much seen what you just approved — most visibly for an admin, whose own submissions land immediately and would otherwise announce themselves back. Tracked by entry id rather than by bumping the last-viewed clock, so approving one thing doesn't quietly bury everything else you hadn't read yet
- [X] A header button opening a centred dialog, not an inline banner — a banner pushed the panel down on every open for something you usually only glance at. Digest, pending queue, and members all use the same dialog now, so the header reads as one row of controls

**Frontend — the empty project**

A project with no entries has nothing to summarize and nothing to list, so both modes bottomed out in a one-line refusal — the first thing a new member ever saw.

- [X] Fixed steps explaining the loop: one input box, gate 1, gate 2, summary ↔ IR
- [X] Opening line written for the reader from their profile alone, so even the empty state is re-projected. Served on `/view` (which has no segments to return anyway) and cached per reader
- [X] The welcome prompt is forbidden from asserting anything about the project — there are no entries, so every project claim it could make would be invented. Grounding here is "the only input is the reader's own profile", not a citation check

---

### 9. Document Input

Most of what a team already knows is in a file, not in someone's head waiting to be retyped a sentence at a time. Drop in the spec, the protocol, the meeting transcript, and the facts land in the IR.

**Drag onto the project view — there is no import screen.** A document enters where a message enters, because it *is* a message: a longer one. Dragging a file anywhere over the project view arms a drop target; releasing it runs the same read → propose → submit → merge path a typed sentence runs. Nothing new to learn, and no second way for the IR to be written.

```
        drag a file over the project view
┌────────────────────────────────────────┐
│ MedGuard              [pending][…]     │
│  ┌──────────────────────────────────┐  │
│  ╎                                  ╎  │
│  ╎     Drop to read into MedGuard   ╎  │  ← dashed target over the whole panel
│  ╎     PDF, markdown, or plain text ╎  │
│  ╎                                  ╎  │
│  └──────────────────────────────────┘  │
│ [ say something, or ask…          ][→] │
└────────────────────────────────────────┘
                    ↓
        "Here's what we understood"  ← the same gate 1, 40 proposals deep
```

**The pipeline mostly already handles it.** Interpretation takes text and existing entries and returns operations; a document is just more text. Three things genuinely change at scale, and they are what this milestone is actually about.

**1. It doesn't fit in one call.** A spec has to be chunked, and a chunk boundary must not fall through the middle of a fact — "sampling was raised to" / "2 kHz" extracted separately is worse than useless.

**2. Extraction has to reconcile with itself.** The same fact stated in an abstract, a table, and an appendix must produce one operation, not three. Within a document this is new work: `/input` only ever reconciled against *stored* entries, never against other proposals in the same batch.

**3. Review is the real problem.** A 20-page spec might yield 80 proposals, and "confirm 80 changes" is a button nobody reads before clicking. Gate 1 exists so a person actually looks at what we understood; 80 cards defeats that by exhaustion. This is the part most likely to need a different answer than the typed-message path, not a scaled-up version of it.

Settled:

- **Same two gates.** A document proposes; the dropper submits; an admin merges. A file is not a licence to write to the IR directly.
- **The file is not stored.** We keep its name and the passage a fact came from, not the bytes — this is a fact store, not a document store. Revisit only if provenance needs the original.
- **One document, one batch.** Dropping two files is two runs, so a bad extraction from one doesn't contaminate review of the other.

**Backend**

- [ ] `POST /projects/:id/document` — multipart upload, member-only, returns proposals and stores **nothing**, mirroring `/input`
- [ ] Text extraction for PDF, markdown and plain text; reject anything else with a clear message rather than extracting garbage
- [ ] Chunk into passages small enough to extract from, overlapping enough that a fact spanning a boundary survives
- [ ] Reconcile across chunks: the same fact restated in a summary and an appendix updates one proposal, not three
- [ ] Reconcile against existing entries too, so a document restating what the project already records produces `update`s rather than duplicates
- [ ] Provenance on each proposal: document name and where in it the fact came from. `source_quote` must stay verbatim, which is harder once the source is a file rather than something the author just typed — the citation should point at the document and location, not only the quote
- [ ] Size and page ceiling, refused up front. A 300-page PDF is a cost and latency incident, not a demo
- [ ] Tests: chunk boundaries don't split facts, restated facts reconcile, a non-member is refused

**Frontend**

- [ ] Drop target over the project view — armed on dragover, dismissed on dragleave or Escape, so you can't get stuck in it
- [ ] Reject unsupported types on drop, before uploading
- [ ] Progress while it reads: a 20-page spec is many model calls, and a silent minute reads as a hang
- [ ] Review at volume — the open question. Grouping by subject, or confidence-based triage, or accepting that a document import is reviewed differently from a sentence. Whatever it is, it must not be 80 cards and a Submit button
- [ ] Each proposal shows the passage it came from, so checking one doesn't mean re-reading the document
- [ ] Nothing is stored until submit, exactly as with a typed message — a bad extraction dropped at gate 1 leaves no trace

---

### Future

- [ ] Conflict detection between contradictory statements
- [ ] Project change timeline view
- [ ] Third party integration
- [ ] Evidence tracking for external sources
- [ ] Change ir entry schema for content to be a string instead of object
