import json
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from .utils.safeparse import safe_parse_json

from .config import MODEL_NAME, QUALIFICATION_INTENT_THRESHOLD, create_async_llm_client
from .models import PqlRecordIn, QualificationResult, QualificationLLMOutput
from .supabase_client import update_row, log_activity


client = create_async_llm_client()


QUALIFICATION_SYSTEM_PROMPT = """
You normalize a single, possibly unstructured last_active value for a product user.

You will be given JSON with:
{
  "last_active_raw": "<original last_active value>",
  "today": "<YYYY-MM-DD>"
}

Interpret how many whole days have passed between last_active_raw and today.
Examples of last_active_raw:
- "2025-02-16"
- "Feb 10, 2025"
- "yesterday"
- "3 days ago"

Respond ONLY in JSON with:
{
  "days_since_last_active": <integer or null>
}

Rules:
- If you can confidently resolve last_active_raw into an absolute date, compute the integer day difference.
- If you cannot, set days_since_last_active to null.
- Do not include any other keys or prose.
"""


def _days_since(date_str: str | None) -> int | None:
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str).date()
    except ValueError:
        return None
    today = datetime.now(timezone.utc).date()
    return (today - dt).days


def _normalize_threshold(value: int | None) -> int:
    if value is None:
        value = QUALIFICATION_INTENT_THRESHOLD
    try:
        parsed = int(value)
    except Exception:
        parsed = QUALIFICATION_INTENT_THRESHOLD
    return max(1, min(10, parsed))


async def run_qualification(
    pql: PqlRecordIn,
    qualification_threshold: int | None = None,
) -> Tuple[QualificationResult, Dict[str, Any]]:
    usage = pql.product_usage_score or 0.0
    threshold = _normalize_threshold(qualification_threshold)
    low_usage_cutoff = max(1, threshold - 3)
    # Prefer the original free-text "Last Active" value from raw_data,
    # falling back to the structured last_active_date column.
    last_active_raw = pql.last_active_date
    if pql.raw_data:
        last_active_raw = (
            pql.raw_data.get("last_active_date")
            or pql.raw_data.get("last_active")
            or pql.raw_data.get("Last Active")
            or last_active_raw
        )

    # Let the LLM normalize the unstructured last_active value into a day count
    days_from_llm: int | None = None
    if last_active_raw:
        today_iso = datetime.now(timezone.utc).date().isoformat()
        context = {
            "last_active_raw": last_active_raw,
            "today": today_iso,
        }
        user_prompt = json.dumps(context, ensure_ascii=False)

        resp = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": QUALIFICATION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = (resp.choices[0].message.content or "").strip()
        parsed = safe_parse_json(content)
        try:
            llm_out = QualificationLLMOutput.model_validate(parsed)
            days_from_llm = llm_out.days_since_last_active
        except Exception:
            days_from_llm = None

    # Fallback to simple ISO parsing if the LLM couldn't resolve it
    days = days_from_llm
    if days is None:
        days = _days_since(last_active_raw)

    # Deterministic rules based only on usage and days
    status = pql.status or "pending"
    # Treat high-usage leads as qualified if they are clearly recent
    # or if recency could not be resolved.
    high_usage_and_recent = usage >= threshold and (days is None or days <= 2)
    # Unfit baseline: low usage AND not recently active.
    unfit_low_usage_and_stale = usage <= low_usage_cutoff and (days is not None and days > 5)

    if high_usage_and_recent:
        status = "qualified"
    elif unfit_low_usage_and_stale:
        status = "rejected"

    # Simple, rule-based summary and AI-style reasoning using only provided fields
    if status == "qualified":
        qualification_result = f"Qualified: usage {usage}/10, last active {days} day(s) ago."
        ai_reasoning = (
            "This lead is qualified because their usage score meets or exceeds the "
            f"threshold of {threshold}/10 and their last active time is within 2 days (or "
            "could not be resolved but appears recent)."
        )
    elif status == "rejected":
        qualification_result = f"Unfit: usage {usage}/10, last active {days} day(s) ago."
        ai_reasoning = (
            "This lead is considered unfit because their usage score is relatively "
            f"low ({low_usage_cutoff}/10 or below) and they have not been active in more "
            "than 5 days, which together indicate low intent and recency."
        )
    else:
        qualification_result = f"Potential: usage {usage}/10, last active {days} day(s) ago."
        ai_reasoning = (
            "This lead is a potential fit but does not yet meet the automatic "
            f"qualification bar of usage >= {threshold}/10 within the last 2 days, and does not "
            "fall into the low-usage-and-stale unfit bucket. A human may still "
            "choose to engage based on other context."
        )

    result = QualificationResult(
        id=pql.id,
        qualification_result=qualification_result,
        agent_metadata={
            "usage_score": usage,
            "qualification_threshold": threshold,
            "low_usage_cutoff": low_usage_cutoff,
            "last_active_raw": last_active_raw,
            "days_since_last_active": days,
            "ai_reasoning": ai_reasoning,
        },
        status=status,
    )

    # Persist back to Supabase
    update_row(
        "pqls",
        pql.id,
        {
            "qualification_result": qualification_result,
            "agent_metadata": result.agent_metadata,
            "status": status,
        },
    )
    log_activity(
        pql.id,
        "qualification_evaluated",
        {
            "usage_score": usage,
            "qualification_threshold": threshold,
            "last_active_raw": last_active_raw,
            "days_since_last_active": days,
            "status": status,
        },
    )

    return result, result.agent_metadata
