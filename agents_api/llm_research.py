import json
from typing import Any, Dict

from .utils.safeparse import safe_parse_json
from .utils.website_hint import infer_website_hint

from .config import MODEL_NAME, create_async_llm_client
from .models import PqlRecordIn, ResearchResult
from .supabase_client import insert_row, update_row, log_activity, get_single_row
from .web_navigate import gather_subject_context_async

client = create_async_llm_client()

RESEARCH_SYSTEM_PROMPT = """
You are a GTM research analyst researching product-qualified leads.

Given basic account + contact context, infer structured information about the company
and key contacts involved in the deal.

You may receive web_navigation context from lightweight web navigation tools.
Use it as supporting evidence when available. If web_navigation is missing or sparse,
proceed conservatively from the provided lead context.

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


async def run_research(
    pql: PqlRecordIn,
    research_metadata: Dict[str, Any] | None = None,
) -> ResearchResult:
    raw = pql.raw_data or {}
    website_hint = infer_website_hint(pql.email, pql.company_name)

    subject = pql.company_name or pql.email
    web_navigation = await gather_subject_context_async(
        subject=subject,
        website_hint_url=website_hint.get("url"),
    )

    context = {
        "id": pql.id,
        "email": pql.email,
        "company_name": pql.company_name,
        "website_hint_url": website_hint.get("url"),
        "website_hint_source": website_hint.get("source"),
        "product_usage_score": pql.product_usage_score,
        "last_active_date": pql.last_active_date,
        "research": research_metadata or {},
        "raw_data": raw,
        "web_navigation": web_navigation,
    }

    user_prompt = (
        "Research this product-qualified lead with company and contact insights.\n\n"
        "Prefer web_navigation evidence when it is present. "
        "If evidence is weak, return conservative defaults.\n\n"
        f"Lead JSON:\n{json.dumps(context, ensure_ascii=False)}\n\n"
        "Return only the JSON object described in the instructions."
    )

    resp = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": RESEARCH_SYSTEM_PROMPT},
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

    has_web_sources = bool(web_navigation.get("sources"))
    research_source = "openai_inferred_with_web_navigate" if has_web_sources else "openai_inferred"

    # Keep the DB contract stable while we migrate naming to "research" in code.
    payload = {
        "pql_id": pql.id,
        "company_info": company_info,
        "key_contacts": key_contacts,
        "enrichment_source": research_source,
    }

    # Upsert into existing enrichments table to avoid schema changes right now.
    existing = get_single_row("enrichments", filters={"pql_id": pql.id})
    if existing:
        update_row("enrichments", existing["id"], payload)
    else:
        insert_row("enrichments", payload)

    log_activity(
        pql.id,
        "researched",
        {
            "company_info_keys": list(company_info.keys()),
            "web_source_count": len(web_navigation.get("sources", [])),
        },
    )

    return ResearchResult(
        pql_id=pql.id,
        company_info=company_info,
        key_contacts=key_contacts,
        research_source=research_source,
    )
