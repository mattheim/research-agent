import json
from typing import Any, Dict

from .utils.safeparse import safe_parse_json
from .utils.website_hint import infer_website_hint

from .config import MODEL_NAME, create_async_llm_client
from .models import PqlRecordIn, EnrichmentResult
from .supabase_client import insert_row, update_row, log_activity, get_single_row

client = create_async_llm_client()

ENRICHMENT_SYSTEM_PROMPT = """
You are a GTM research analyst enriching product-qualified leads.

Given basic account + contact context, infer structured information about the company
and key contacts involved in the deal.

You may receive a website_hint_url. Use it only as a hint for likely company context.
Do NOT claim you visited, verified, or read any website content.
If website_hint_url is missing, proceed from the provided lead context only.

Respond ONLY in JSON with the following shape:
{
  "company_info": {
    "industry": "<string>",
    "size_bucket": "<e.g. SMB, Mid-market, Enterprise>",
    "hq_country": "<string>",
    "key_initiatives": ["strings"],
    "primary_product": "<string>",
    "current_tools": ["strings"]
  },
  "key_contacts": [
    {
      "name": "<string or null>",
      "title": "<string or null>",
      "role_in_deal": "<economic_buyer|champion|user|other>",
      "email": "<string or null>",
      "notes": "<short text>"
    }
  ]
}
"""


async def run_enrichment(pql: PqlRecordIn, qualification_metadata: Dict[str, Any]) -> EnrichmentResult:
    raw = pql.raw_data or {}
    website_hint = infer_website_hint(pql.email, pql.company_name)

    context = {
        "id": pql.id,
        "email": pql.email,
        "company_name": pql.company_name,
        "website_hint_url": website_hint.get("url"),
        "website_hint_source": website_hint.get("source"),
        "product_usage_score": pql.product_usage_score,
        "last_active_date": pql.last_active_date,
        "qualification": qualification_metadata,
        "raw_data": raw,
    }

    user_prompt = (
        "Enrich this product-qualified lead with company and contact insights.\n\n"
        "Use website_hint_url only as a probable homepage/domain cue. "
        "Do not fabricate claims about page content.\n\n"
        f"Lead JSON:\n{json.dumps(context, ensure_ascii=False)}\n\n"
        "Return only the JSON object described in the instructions."
    )

    resp = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": ENRICHMENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = (resp.choices[0].message.content or "").strip()
    parsed = safe_parse_json(content)

    company_info = parsed.get("company_info") if isinstance(parsed, dict) else None
    key_contacts = parsed.get("key_contacts") if isinstance(parsed, dict) else None

    if not isinstance(company_info, dict):
        company_info = {}
    if not isinstance(key_contacts, list):
        key_contacts = []

    payload = {
        "pql_id": pql.id,
        "company_info": company_info,
        "key_contacts": key_contacts,
        "enrichment_source": "openai_inferred",
    }

    # Upsert enrichment so we can safely re-run it without creating duplicates.
    existing = get_single_row("enrichments", filters={"pql_id": pql.id})
    if existing:
        update_row("enrichments", existing["id"], payload)
    else:
        insert_row("enrichments", payload)

    log_activity(
        pql.id,
        "enriched",
        {"company_info_keys": list(company_info.keys())},
    )

    return EnrichmentResult(
        pql_id=pql.id,
        company_info=company_info,
        key_contacts=key_contacts,
        enrichment_source="openai_inferred",
    )
