from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import ensure_supabase_config, create_async_llm_client, MODEL_NAME, LLM_PROVIDER
from .llm_email_generation import generate_email_draft
from .llm_enrichment import run_enrichment
from .llm_qualification import run_qualification
from .models import (
    EnrichRequest,
    EmailDraftResult,
    EnrichmentResult,
    PqlRecordIn,
    QualifyRequest,
    QualifyResponse,
    RegenerateEmailRequest,
)
from .supabase_client import get_single_row, log_activity


app = FastAPI(title="PQL Agents API", version="0.1.0")

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


@app.post("/qualify", response_model=QualifyResponse)
async def qualify(request: QualifyRequest) -> QualifyResponse:
    if not request.pqls:
        return QualifyResponse(qualified=[])

    qualified: List = []

    for pql in request.pqls:
        # 1) Qualification
        qual_result, qual_metadata = await run_qualification(
            pql,
            qualification_threshold=request.qualification_threshold,
        )

        # 2) Enrichment runs for all leads so reviewers always see company context,
        #    even if a lead is not yet qualified.
        enrichment = await run_enrichment(pql, qual_metadata)

        # 3) Generate email drafts (and AI reasoning) for all leads so
        #    reviewers can inspect the agent's proposal even when the
        #    lead is not yet qualified. The Approve & Send button in
        #    the UI is still gated by status.
        await generate_email_draft(pql, enrichment, qual_metadata)

        # 4) Only report truly qualified leads back to the frontend
        if qual_result.status == "qualified":
            qualified.append(qual_result)

    return QualifyResponse(qualified=qualified)


@app.post("/pqls/{pql_id}/regenerate-email", response_model=EmailDraftResult)
async def regenerate_email(pql_id: str, body: RegenerateEmailRequest) -> EmailDraftResult:
    # Fetch PQL and enrichment from Supabase
    pql_row = get_single_row("pqls", filters={"id": pql_id})
    if not pql_row:
        raise HTTPException(status_code=404, detail="PQL not found")

    enrichment_row = get_single_row("enrichments", filters={"pql_id": pql_id})
    if not enrichment_row:
        raise HTTPException(status_code=400, detail="No enrichment found for this PQL")

    pql = PqlRecordIn(
        id=pql_row["id"],
        email=pql_row["email"],
        company_name=pql_row.get("company_name"),
        product_usage_score=pql_row.get("product_usage_score"),
        last_active_date=pql_row.get("last_active_date"),
        raw_data=pql_row.get("raw_data") or {},
        status=pql_row.get("status", "pending"),
    )

    qualification_metadata = (pql_row.get("agent_metadata") or {}) if isinstance(pql_row.get("agent_metadata"), dict) else {}

    enrichment = EnrichmentResult(
        pql_id=pql_id,
        company_info=enrichment_row.get("company_info") or {},
        key_contacts=enrichment_row.get("key_contacts") or [],
        enrichment_source=enrichment_row.get("enrichment_source") or "openai_inferred",
    )

    if body.override_context:
        # Attach override context into qualification metadata for the new draft
        qualification_metadata = {
            **qualification_metadata,
            "override_context": body.override_context,
        }

    draft = await generate_email_draft(pql, enrichment, qualification_metadata)
    log_activity(pql_id, "email_regenerated", {"subject": draft.subject})
    return draft


@app.post("/pqls/{pql_id}/enrich", response_model=EnrichmentResult)
async def enrich_pql(pql_id: str, body: EnrichRequest | None = None) -> EnrichmentResult:
    """
    Re-run qualification + enrichment (and regenerate draft) for a single PQL.

    This "replays" the pipeline for that PQL, starting from a neutral
    status of 'pending', so previously marked Unfit leads can move back
    into Potential or Qualified if they meet the rules.
    """
    pql_row = get_single_row("pqls", filters={"id": pql_id})
    if not pql_row:
        raise HTTPException(status_code=404, detail="PQL not found")

    # Reset status to 'pending' so re-qualification is not "sticky" to a prior
    # human Unfit decision.
    pql = PqlRecordIn(
        id=pql_row["id"],
        email=pql_row["email"],
        company_name=pql_row.get("company_name"),
        product_usage_score=pql_row.get("product_usage_score"),
        last_active_date=pql_row.get("last_active_date"),
        raw_data=pql_row.get("raw_data") or {},
        status="pending",
    )

    # Re-run qualification from scratch.
    _qual_result, qual_metadata = await run_qualification(
        pql,
        qualification_threshold=body.qualification_threshold if body else None,
    )

    # Re-run enrichment and regenerate draft with the latest qualification.
    enrichment = await run_enrichment(pql, qual_metadata)
    await generate_email_draft(pql, enrichment, qual_metadata)

    return enrichment


@app.get("/health")
async def health() -> dict:
  return {"status": "ok", "provider": LLM_PROVIDER, "model": MODEL_NAME}


@app.get("/llm-test")
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
