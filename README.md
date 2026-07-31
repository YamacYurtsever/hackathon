# Contextor

An n-way translator between professional contexts — see `CLAUDE.md` for the full pitch and design.

## Running locally

### Backend (Flask)

```bash
cd backend
source venv/bin/activate
python src/app.py
```

Runs on http://localhost:5001 (not 5000 — macOS AirPlay Receiver squats on that port). Check it's up with `curl http://localhost:5001/api/health`.

Seeded demo accounts: `engineer`, `biologist`, `lawyer`, `business` — all with password `medguard`.

They share four projects but not all of them, and each administers a different one, so every account sees a different home page. Halo Infusion Pump boots with changes waiting for its admin; NORTHSTAR Trial Ops boots with a live conflict.

### Frontend (React + Vite)

```bash
cd frontend
nvm use   # picks up .nvmrc (Node 22.21.0)
npm run dev
```

Runs on http://localhost:5173.
