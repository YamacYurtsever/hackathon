# AGENTS.md — Context Translator

## Problem Statement
How might AI help multi-disciplinary teams make sense of information, present ideas, align on decisions, and review work more effectively?

## Pitch
An n-way translator — not between languages, but between professional contexts. A project's ground truth lives in a neutral Intermediate Representation (IR). Every team member reads and writes that IR through a lens shaped by their role, their history on the project, and their own stated expertise — so an engineer, a biologist, a lawyer, and a business lead can all work off the same facts without forcing anyone into layman's terms.

## Core Pipeline
```
Domain-specific input (natural language)
        ↓
   Intermediate Representation (IR)   ← neutral, structured, source of truth
        ↓
Domain-specific output (re-projected for reader's role + context + history)
```

This is **re-projection, not literal translation**: the output can surface implications the original sentence didn't state outright (e.g. "this sensor change may require re-running your validation study"). That's the wow-factor, but it's also the hallucination risk — every inferred claim shown to a user must be traceable back to a specific IR field. No ungrounded claims.

## Demo Scenario (build everything against this)
**MedGuard** — a clinical device team: **Engineer**, **Biologist**, **Lawyer** (regulatory), **Business/Ops lead**.

Example flow:
1. Engineer posts: *"Bumped sampling rate to 2kHz, added debounce filter, should cut false positives."*
2. Parsed into IR: `{change: sensor sampling + filtering, owner: engineer, affects: [validation protocol, FDA submission specs, timeline]}`
3. Biologist's view: flags need to re-run false-positive validation.
4. Lawyer's view: flags possible 510(k) supplement filing.
5. Business view: flags ~2 week timeline/cost impact.

Same fact, three honestly different, useful, non-obvious re-projections — each one citing which IR field triggered it.

## Context Model
Keep these three layers distinct in the schema even if the UI blends them:

1. **Role/discipline lens** — vocabulary, units, framing conventions
2. **Project history** — what this person already knows, so outputs don't over-explain
3. **Stake/permissions** — what they can see or amend

## Feature Backlog (from brainstorm, roughly prioritized)

**Must-have for demo:**
- [ ] Natural language → IR extraction (Mistral)
- [ ] IR → role-specific re-projection (Mistral)
- [ ] Context profile per user (role, self-described expertise, past project blurbs)
- [ ] Cross-role effect propagation (the ripple-effect wow moment)
- [ ] Grounding: every re-projected claim references its source IR field
- [ ] NL/IR toggle: single click switches a view between natural-language summary and raw IR (or IR diff, for amendments) — applies to both project summaries and amendment review
- [ ] "Since you last viewed" summary: client stores last-viewed timestamp per project locally, requests changes since then, displays a digest of what changed on project open
- [ ] Every IR addition/change stored with a timestamp (and ideally author) server-side — required for both version history and the "since last viewed" digest to work

**Should-have if time allows:**
- [ ] Meaning-preservation check — second AI pass compares re-projected output back against the IR to confirm it didn't drift or invent claims
- [ ] Amendment flow: user proposes a change in their own language → converts to IR diff → admin/owner approves before it's applied
- [ ] Version history on the IR (who changed what, when)
- [ ] Attribution: track who authored which IR fact, with timestamp

**Nice-to-have / stretch:**
- [ ] Conflict detection — flag when two people's statements imply contradictory IR states
- [ ] Conflict resolution UX (voting, discussion thread, admin override)
- [ ] Ask-the-IR chat — query project state/history conversationally instead of browsing
- [ ] Evidence tracking for external sources cited in summaries
- [ ] One real third-party integration (Atlassian API) pulling live items into IR; other "connected apps" can be mocked in UI

**Explicitly out of scope for this hackathon:**
- Multiple simultaneous real integrations
- Fine-grained permission system beyond basic role checks
- Production-grade conflict resolution (mediation logic etc.)

## Tech Stack
- **Frontend:** React + shadcn, ESLint
- **Backend:** Python + Flask, Vulture (dead code detection)
- **LLM:** Mistral — core engine for IR extraction and re-projection

## Development Workflow

### Backend (Flask)
```bash
cd backend
source venv/bin/activate
python app.py
```
Runs on http://127.0.0.1:5000. Check it's up with `curl http://127.0.0.1:5000/api/health`.

### Frontend (React + Vite)
```bash
cd frontend
nvm use   # picks up .nvmrc (Node 22.21.0)
npm run dev
```
Runs on http://localhost:5173.

## Suggested Team Split (5 people, ~24 hrs)
1. **IR + prompting lead** — designs IR schema, owns extraction & re-projection prompts, grounding checks
2. **Backend/data** — Flask API, IR storage, amendment/versioning logic
3. **Frontend — project/IR view** — shared project feed, timeline, version history
4. **Frontend — role & query UI** — context profile setup, personalized view, ask-the-IR interface
5. **Integrations + scenario + pitch** — Atlassian API hookup, MedGuard seed data, deck, demo script

## Milestones

### 1. Foundation
- [ ] IR JSON schema drafted and agreed by whole team
- [ ] Context profile schema drafted
- [ ] Repo scaffolded (React+shadcn frontend, Flask backend, basic routes)
- [ ] MedGuard scenario fully scripted (exact input messages, exact expected outputs per role)

### 2. Core Pipeline
- [ ] NL → IR extraction working via Mistral (single message in, IR object out)
- [ ] IR → role-specific re-projection working (IR in, role-flavored text out)
- [ ] Context profile actually influences re-projection output (not just role — history/expertise too)
- [ ] Basic Flask endpoints: create project, post message, fetch re-projected view per user, fetch changes-since-timestamp

### 3. Wow-Factor Feature
- [ ] Cross-role effect propagation: one IR update triggers relevant flags for other roles
- [ ] Grounding citations visible in UI (which IR field produced this claim)
- [ ] Frontend: project feed + per-role personalized view rendering correctly
- [ ] NL/IR toggle on project summary view (flip between re-projected text and raw IR)
- [ ] "Since you last viewed" digest: local last-viewed timestamp per project, fetch + display re-projected summary of changes since then, on project open

### 4. Depth Features (pick based on remaining time)
- [ ] Meaning-preservation check pass
- [ ] Amendment proposal + admin approval flow, with NL/IR toggle showing the change as plain-language diff or raw IR diff
- [ ] Version history view
- [ ] Attribution UI (surface who said what, when — the underlying data is already stored per the must-have above)

### 5. Integration + Polish
- [ ] Atlassian API integration pulling at least one real data point into IR
- [ ] UI polish pass (shadcn components consistent, empty/loading states handled)
- [ ] Lint/dead-code pass (ESLint, Vulture)

### 6. Demo Prep
- [ ] Full scripted run-through of MedGuard scenario end-to-end, timed
- [ ] Backup plan if live demo fails (recorded video / screenshots)
- [ ] Deck finalized: problem → "n-way context translator" framing → live demo → architecture slide → what's next

## Guardrails (keep repeating to the team)
- Every AI-generated claim shown to a user must be traceable to an IR field. If it can't cite its source, don't show it as fact.
- Build the demo scenario first, schema second, generic support last. Don't generalize before the one scenario works end-to-end.
- Query path (read) is low-risk and should be rock-solid. Amendment path (write) is higher-risk — fine if it's scripted/narrow for the demo.
