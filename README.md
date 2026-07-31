# Relay IR — Context Translator

Relay IR turns documents into a neutral, structured source of truth using
Mistral AI. Upload a PDF, DOCX, PPTX, or image; the backend uses Mistral OCR,
extracts atomic IR entries against the schemas in `backend/schemas`, and returns
a stable project ID. Questions sent with that ID are answered from its IR only,
with entry- and page-level citations.

## How it works

```text
PDF / document / image
        │
        ▼
Mistral OCR (page-aware Markdown)
        │
        ▼
Mistral structured extraction
        │
        ├── quote checked against OCR source
        └── stored as schema-valid atomic IR entries
                │
                ▼
          stable project ID
                │
                ▼
       grounded Q&A + IR citations
```

The server stores generated JSON under `backend/data/` and does not persist the
uploaded original. Each project follows `project.schema.json`; each atomic fact
follows `ir_entry.schema.json`.

## Run locally

### 1. Backend

Python 3.10+ is required.

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your Mistral API key to `backend/.env`:

```dotenv
MISTRAL_API_KEY=your_key_here
```

Then start Flask:

```bash
python app.py
```

The API runs at `http://127.0.0.1:5000`. Verify it with:

```bash
curl http://127.0.0.1:5000/api/health
```

### 2. Frontend

```bash
cd frontend
nvm use
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to the Flask backend.

## API

Upload a document:

```bash
curl -F "file=@example.pdf" http://127.0.0.1:5000/api/documents
```

The response includes a project ID such as `prj_12ab34cd56ef`. Use it to load
the IR:

```bash
curl http://127.0.0.1:5000/api/projects/prj_12ab34cd56ef
```

Ask that IR a question:

```bash
curl \
  -H "Content-Type: application/json" \
  -d '{"question":"What are the key requirements?"}' \
  http://127.0.0.1:5000/api/projects/prj_12ab34cd56ef/questions
```

An answer is accepted only when its citation IDs exist in that project. If
Mistral cites an unknown ID, the server fails closed and returns an
insufficient-evidence response.

## Checks

```bash
cd backend
pytest
vulture

cd ../frontend
npm run lint
npm run build
```
