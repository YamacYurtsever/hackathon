# Context Translator

An n-way translator between professional contexts — see `CLAUDE.md` for the full pitch and design.

## Running locally

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
