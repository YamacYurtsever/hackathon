# Relay IR — Context Translator

Relay IR gives multidisciplinary teams one neutral project source of truth
without forcing everyone into the same vocabulary. People post updates in their
own language; Mistral extracts atomic IR entries, then re-projects those entries
through each reader's free-form context profile.

There are no fixed roles in the code. A profile can describe any mixture of
expertise, responsibilities, history, and communication preferences.

## Core flow

```text
Natural-language project update
        │  + author's free-form context
        ▼
Mistral structured extraction
        │
        ├── atomic, neutral IR entries
        ├── author + server timestamp
        └── verified supporting quote
                │
                ▼
       project source of truth
                │  + viewer's free-form context
                ▼
Mistral re-projection
        │
        ├── viewer-relevant framing and implications
        └── exact IR entry + content paths
```

The server drops any re-projected claim whose entry ID or grounding path does
not exist. Document ingestion remains available: PDFs, DOCX, PPTX, and images
go through Mistral OCR before entering the same IR pipeline.

## Features

- File-backed projects, profiles, IR entries, documents, and version records.
- Natural-language update → structured IR extraction.
- Profile-shaped re-projection with server-validated grounding paths.
- Project creator automatically becomes the first member and administrator.
- Admin promotion and safe project exit with last-admin auto-promotion.
- Changes-since endpoint and a local “since you last viewed” frontend digest.
- Natural, personalized, and raw-JSON views.
- Clickable grounding citations and entry attribution.
- Document upload and grounded Ask-the-IR chat.
- Idempotent MedGuard seed script with four example context profiles.

## Run locally

### Backend

Python 3.10+ is required.

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add a standard Mistral inference key to `backend/.env`:

```dotenv
MISTRAL_API_KEY=your_key_here
```

Seed the MedGuard demo, then start Flask:

```bash
python seed.py
python app.py
```

The API runs at `http://127.0.0.1:5000`.

### Frontend

```bash
cd frontend
nvm use
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to Flask.

## Main API

### Profiles

```http
POST /api/profiles
GET  /api/profiles
GET  /api/profiles/:id
```

Example profile:

```json
{
  "content": {
    "name": "Maya Chen",
    "expertise": "Embedded sensor firmware and signal acquisition",
    "history": "Owns the MedGuard sensor implementation",
    "preferences": "Show units, technical trade-offs, and concrete failure modes"
  }
}
```

### Projects and updates

```http
POST /api/projects
GET  /api/projects
GET  /api/projects/:id
POST /api/projects/:id/messages
GET  /api/projects/:id/changes?since=<ISO-8601>
```

Create a project:

```json
{
  "name": "MedGuard",
  "creator_id": "user_engineer"
}
```

Add an update:

```json
{
  "author_id": "user_engineer",
  "text": "Bumped sampling rate to 2kHz and added a debounce filter."
}
```

### Personalized view

```http
GET /api/projects/:id/view?user_id=user_biologist
```

Each returned claim contains an `entry_id` plus a `grounding` array of validated
paths such as `content.statement`. Claims without a valid path are removed.

### Administration and history

```http
POST /api/projects/:id/promote
POST /api/projects/:id/exit
GET  /api/entries/:entry_id/versions
```

Promotion requires a `caller_id` that is already in `project.admins`. If the
last admin exits while members remain, the server promotes another member.

### Documents and Q&A

```http
POST /api/documents
POST /api/projects/:id/questions
```

Upload:

```bash
curl \
  -F "file=@example.pdf" \
  -F "author_id=user_engineer" \
  http://127.0.0.1:5000/api/documents
```

## Verification

```bash
cd backend
pytest
vulture

cd ../frontend
npm run lint
npm run build
```
