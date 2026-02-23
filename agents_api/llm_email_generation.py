import json
from typing import Any, Dict

from .utils.safeparse import safe_parse_json
from .utils.website_hint import infer_website_hint

from .config import MODEL_NAME, create_async_llm_client
from .models import EmailDraftResult, EnrichmentResult, PqlRecordIn
from .supabase_client import insert_row, update_row, log_activity


client = create_async_llm_client()


EMAIL_SYSTEM_PROMPT = """
You write short, outbound follow-ups after a successful product call, aimed at booking qualified meetings.

Use:
- Product usage and account context
- Enrichment data (company info and key contacts)

Your goal is to:
- Propose a highly relevant offer (e.g., pilot, ROI analysis, deeper technical workshop)
- Write a concise, confident, human email that clearly asks for the next meeting.

You may receive a website_hint_url. Use it as a lightweight relevance cue only.
Do NOT claim you visited or verified website content.

Respond ONLY in JSON with the following shape:
{
  "subject": "<short engaging subject>",
  "body": "<3-5 sentence email body>",
  "proposed_offer": "<short description of the concrete offer>",
  "ai_reasoning": "<why this offer and message are a good fit>"
}
"""


async def generate_email_draft(
    pql: PqlRecordIn,
    enrichment: EnrichmentResult,
    qualification_metadata: Dict[str, Any],
) -> EmailDraftResult:
    website_hint = infer_website_hint(pql.email, pql.company_name)

    context = {
        "pql": {
            "id": pql.id,
            "email": pql.email,
            "company_name": pql.company_name,
            "product_usage_score": pql.product_usage_score,
            "last_active_date": pql.last_active_date,
            "raw_data": pql.raw_data or {},
        },
        "website_hint_url": website_hint.get("url"),
        "website_hint_source": website_hint.get("source"),
        "qualification": qualification_metadata,
        "enrichment": {
            "company_info": enrichment.company_info,
            "key_contacts": enrichment.key_contacts,
        },
    }

    user_prompt = (
        "Write a follow-up email that will help book a qualified meeting.\n\n"
        "Use website_hint_url only as a likely domain/homepage cue. "
        "Do not fabricate claims about site content.\n\n"
        "Use the JSON below as context and return ONLY the JSON object described.\n\n"
        f"{json.dumps(context, ensure_ascii=False)}"
    )

    resp = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": EMAIL_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = (resp.choices[0].message.content or "").strip()
    parsed = safe_parse_json(content)

    if not isinstance(parsed, dict):
        parsed = {"subject": "Quick follow-up", "body": content, "proposed_offer": "", "ai_reasoning": ""}

    subject = (parsed.get("subject") or "Quick follow-up").strip()
    body = (parsed.get("body") or "").strip()
    proposed_offer = (parsed.get("proposed_offer") or "").strip()
    ai_reasoning = (parsed.get("ai_reasoning") or "").strip()

    row = insert_row(
        "email_drafts",
        {
            "pql_id": pql.id,
            "to_email": pql.email,
            "subject": subject,
            "body": body,
            "proposed_offer": proposed_offer,
            "ai_reasoning": ai_reasoning,
            "is_edited": False,
        },
    )
    log_activity(
        pql.id,
        "draft_generated",
        {"subject": subject, "proposed_offer": proposed_offer},
    )

    return EmailDraftResult(
        pql_id=pql.id,
        to_email=row.get("to_email", pql.email),
        subject=row.get("subject", subject),
        body=row.get("body", body),
        proposed_offer=row.get("proposed_offer", proposed_offer),
        ai_reasoning=row.get("ai_reasoning", ai_reasoning),
    )
