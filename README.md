# HEIM_GTM Monorepo

This repository contains the full HEIM_GTM app:

- `agents_api` - FastAPI backend that qualifies, enriches, and drafts outreach content.
- `frontend-service` - React/Vite frontend for the PQL command center.

## Prerequisites

- Python 3.10+
- Node.js 18+ and npm

## Repository layout

```text
.
├── agents_api
└── frontend-service
```

## 1) Backend setup (`agents_api`)

```bash
cd agents_api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set real values in `agents_api/.env`:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `LLM_PROVIDER` (`openai` or `ollama`)
- `OPENAI_API_KEY` (required for `openai`)
- `MODEL_NAME`

Start backend:

```bash
cd agents_api
source .venv/bin/activate
uvicorn agents_api.main:app --reload --port 8000
```

## 2) Frontend setup (`frontend-service`)

```bash
cd frontend-service
npm install
cp .env.example .env
```

Set real values in `frontend-service/.env`:

- `VITE_SUPABASE_PROJECT_ID`
- `VITE_SUPABASE_PUBLISHABLE_KEY`
- `VITE_SUPABASE_URL`

Start frontend:

```bash
cd frontend-service
npm run dev
```

The app runs on `http://localhost:8080` and expects the backend at `http://localhost:8000`.

## Supabase migrations

From `frontend-service`:

```bash
npx supabase migration list
npx supabase db diff --linked
```

## Notes

- Local secrets are ignored via root `.gitignore` (`**/.env`, `**/.env.*`).
- Supabase local state is ignored (`**/supabase/.temp/`).
