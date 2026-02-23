# PQL Agents API

FastAPI-based backend service that powers the PQL → Meeting pipeline for the `pql-pipeline-pilot` Lovable app.  
It qualifies incoming PQLs, enriches them, drafts outreach emails, and updates Supabase.

## Features
- `POST /qualify` – qualify PQLs using usage score + last-active, then enrich and generate email drafts for qualified leads.
- `POST /pqls/{id}/regenerate-email` – regenerate an email draft for a single PQL.
- `GET /health` – simple health check (reports LLM provider/model).
- `GET /llm-test` – sanity check that the configured LLM is reachable.

## Project structure
- `main.py` – FastAPI app and route wiring.
- `config.py` – environment configuration and LLM client factory.
- `models.py` – Pydantic models for requests/responses.
- `llm_qualification.py` – qualification logic and last-active normalization.
- `llm_enrichment.py` – company/contact enrichment via LLM.
- `llm_email_generation.py` – outreach email + offer generation via LLM.
- `supabase_client.py` – minimal Supabase REST client helpers.
- `utils/safeparse.py` – robust JSON parsing for LLM outputs.

## Setup
```bash
cd agents_api
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in this directory with at least:

```bash
LLM_PROVIDER=openai          # or 'ollama'
OPENAI_API_KEY=sk-...
MODEL_NAME=gpt-4o-mini       # or your preferred model

SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

## Running the API

```bash
uvicorn agents_api.main:app --reload --port 8000
```

The frontend (`pql-pipeline-pilot`) should point `AGENTS_API_BASE_URL` to `http://localhost:8000`.

