# PQL Agents API

FastAPI-based backend service that powers the PQL research workflow for the `frontend-service` app.  
It researches incoming PQLs with company/contact intelligence and updates Supabase.

## Features
- `POST /research?pql_id=<id>` – run research for one PQL.
- `GET /web_navigate?subject=<text>&website_hint_url=<optional-url>` – test raw web navigation output.
- `GET /web_nav_google_search?query=<text>` – return top 5 links from Google Custom Search JSON API.
- `GET /health` – simple health check (reports LLM provider/model).
- `GET /llm-test` – sanity check that the configured LLM is reachable.

## Project structure
- `main.py` – FastAPI app and route wiring.
- `config.py` – environment configuration and LLM client factory.
- `models.py` – Pydantic models for requests/responses.
- `llm_research.py` – company/contact research via LLM.
- `web_navigate.py` – web navigation utility (Playwright + fallback HTTP fetch).
- `supabase_client.py` – minimal Supabase REST client helpers.
- `utils/safeparse.py` – robust JSON parsing for LLM outputs.

## Setup
```bash
cd agents_api
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

Before running Google search endpoints, configure Google Custom Search:

- Enable "Custom Search API" in your Google Cloud project.
- Create a Programmable Search Engine and copy its Search Engine ID (`cx`).

Create a `.env` file in this directory with at least:

```bash
LLM_PROVIDER=openai          # or 'ollama'
OPENAI_API_KEY=sk-...
MODEL_NAME=gpt-4o-mini       # or your preferred model

SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Required for /web_nav_google_search (Google Custom Search JSON API):
GOOGLE_SEARCH_API_KEY=...
GOOGLE_SEARCH_CX=...
```

## Running the API

```bash
uvicorn agents_api.main:app --reload --port 8000
```

The frontend (`frontend-service`) should point `AGENTS_API_BASE_URL` to `http://localhost:8000`.
