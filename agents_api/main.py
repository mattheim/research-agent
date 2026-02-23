from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import ensure_supabase_config, create_async_llm_client, MODEL_NAME, LLM_PROVIDER
from .llm_research import run_research
from .models import PqlRecordIn, ResearchRequest, ResearchResult
from .supabase_client import get_single_row
from .web_navigate import gather_subject_context_async, google_search_top_links_async


OPENAPI_TAGS = [
    {
        "name": "Web-Nav",
        "description": "Endpoints for directly testing web navigation",
    },
    {
        "name": "Research",
        "description": "Endpoints that run the lead research workflow.",
    },
    {
        "name": "System",
        "description": "System health and connectivity checks.",
    },
]


app = FastAPI(title="FUCK FUCK FUCK", version="0.1.0", openapi_tags=OPENAPI_TAGS)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _on_startup() -> None:
    # Fail fast if Supabase is not configured.
    ensure_supabase_config()


@app.post("/research", response_model=ResearchResult, tags=["Research"])
async def research(pql_id: str, body: ResearchRequest | None = None) -> ResearchResult:
    """
    Research for a single PQL.

    This route performs company/contact research and writes results to Supabase.
    """
    _ = body  # kept for backward compatibility with existing frontend payloads

    pql_row = get_single_row("pqls", filters={"id": pql_id})
    if not pql_row:
        raise HTTPException(status_code=404, detail="PQL not found")

    pql = PqlRecordIn(
        id=pql_row["id"],
        email=pql_row["email"],
        company_name=pql_row.get("company_name"),
        raw_data=pql_row.get("raw_data") or {},
        status="pending",
    )

    result = await run_research(pql)
    return result


@app.get("/web_navigate", tags=["Web-Nav"])
async def web_navigate(subject: str, website_hint_url: str | None = None) -> dict:
    """
    Direct test endpoint for the web navigation module.
    """
    return await gather_subject_context_async(subject=subject, website_hint_url=website_hint_url)


@app.get("/web_nav_google_search", tags=["Web-Nav"])
async def web_nav_google_search(query: str) -> dict:
    """
    Return the top 5 links from Google Custom Search JSON API for a free-text query.
    """
    return await google_search_top_links_async(query=query, limit=5)


@app.get("/health", tags=["System"])
async def health() -> dict:
    return {"status": "ok", "provider": LLM_PROVIDER, "model": MODEL_NAME}


@app.get("/llm-test", tags=["System"])
async def llm_test() -> dict:
    """
    Simple hello-world style call that exercises the configured LLM.
    """
    client = create_async_llm_client()
    resp = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": "You are a test assistant. Respond with a very short Helllo and say that the system is live and working",
            },
            {"role": "user", "content": "Test the PQL Command Center agents API. Are we live???"},
        ],
    )
    content = (resp.choices[0].message.content or "").strip()
    return {"raw": content}
