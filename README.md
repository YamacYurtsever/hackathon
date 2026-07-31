# Relay IR — Context Translator

Relay IR gives multidisciplinary teams one neutral project source of truth
without forcing everyone into the same vocabulary. People post updates in their
own language; Mistral extracts atomic IR entries, then re-projects those entries
through each reader's free-form context profile.

## Architecture

```text
natural-language update + author's profile
                    ↓
       grounded, neutral IR entries
                    ↓
        file-backed project source of truth
                    ↓
             viewer's profile
                    ↓
 personalized claims with validated IR paths
```

The Flask application in `backend/app.py` is the only backend entry point. It
owns authentication, project membership, file-backed storage, and the Mistral
pipeline. Protected endpoints derive the acting user from the signed session
cookie; client-supplied author, creator, caller, or exit-user IDs are not
trusted.

The React application provides signup/login, editable context profiles, a home
list of joined projects, create/join flows, admin-managed membership, the IR
feed, personalized lenses, changes-since digest, multi-file project ingestion,
Git-style reviewed issue solutions, and grounded Ask-the-IR chat. The project
feed groups atomic IR entries into short source updates; users expand evidence
only when needed or ask the model for a grounded explanation.

## Run locally

Python 3.10+ and the Node version in `frontend/.nvmrc` are required.

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set `MISTRAL_API_KEY` and a random `FLASK_SECRET_KEY` in `backend/.env`, then
start Flask:

```bash
python app.py
```

The API runs at `http://127.0.0.1:5000`. Startup idempotently seeds MedGuard.
The demo usernames are `engineer`, `biologist`, `lawyer`, and `business`; each
uses password `medguard`.

### Frontend

```bash
cd frontend
nvm use
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to Flask.

## Main API

Authentication:

```http
POST /api/signup
POST /api/login
POST /api/logout
GET  /api/me
GET  /api/profiles/:id
PUT  /api/profiles/me
```

Projects and membership:

```http
GET  /api/projects
POST /api/projects
GET  /api/projects/:id
POST /api/projects/:id/join
POST /api/projects/:id/members
DELETE /api/projects/:id/members/:user_id
POST /api/projects/:id/promote
POST /api/projects/:id/exit
```

IR pipeline:

```http
POST /api/projects/:id/messages
POST /api/projects/:id/documents
GET  /api/projects/:id/view?user_id=<member-profile-id>
GET  /api/projects/:id/changes?since=<ISO-8601>
GET  /api/entries/:entry_id/versions
POST /api/projects/:id/questions
POST /api/documents
```

Reviewed issue workflow:

```http
GET  /api/projects/:id/issues
POST /api/projects/:id/issues
POST /api/projects/:id/issues/:issue_id/proposals
POST /api/projects/:id/issues/:issue_id/proposals/:proposal_id/revisions
POST /api/projects/:id/issues/:issue_id/proposals/:proposal_id/submit
POST /api/projects/:id/issues/:issue_id/proposals/:proposal_id/review
```

All project, IR, and profile endpoints require the session cookie. Logout
idempotently clears it. The optional `user_id` on the view endpoint selects a
member's context lens; it does not identify the caller.

`POST /api/documents` creates a new project from a file.
`POST /api/projects/:id/documents` adds another file to an existing project and
automatically appends its grounded entries to that project's IR.

An issue names the expertise required and one or more independent reviewers.
Non-reviewer members can create or append immutable solution revisions. A
contributor submits the current revision, and only an assigned reviewer who did
not contribute can approve it. Approval records the solution as a grounded IR
decision and resolves the issue. Revisions include their base version, so stale
edits are rejected instead of silently overwriting another member's work.

## Verification

```bash
cd backend
pytest
vulture

cd ../frontend
npm run lint
npm run build
```
