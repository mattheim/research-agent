import json
import logging
from typing import Any, Dict, Optional

import requests

from .config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, ensure_supabase_config


logger = logging.getLogger(__name__)


def _base_headers() -> Dict[str, str]:
    ensure_supabase_config()
    return {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }


def _table_url(table: str) -> str:
    ensure_supabase_config()
    return SUPABASE_URL.rstrip("/") + f"/rest/v1/{table}"


def update_row(table: str, row_id: str, data: Dict[str, Any]) -> None:
    url = _table_url(table)
    headers = _base_headers()
    headers["Prefer"] = "return=minimal"
    params = {"id": f"eq.{row_id}"}
    resp = requests.patch(url, headers=headers, params=params, json=data, timeout=10)
    try:
        resp.raise_for_status()
    except Exception:
        logger.exception("Failed to update %s row %s: %s", table, row_id, resp.text)
        raise


def insert_row(table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    url = _table_url(table)
    headers = _base_headers()
    headers["Prefer"] = "return=representation"
    resp = requests.post(url, headers=headers, json=data, timeout=10)
    try:
        resp.raise_for_status()
    except Exception:
        logger.exception("Failed to insert into %s: %s", table, resp.text)
        raise
    try:
        payload = resp.json()
    except json.JSONDecodeError:
        return {}
    if isinstance(payload, list) and payload:
        return payload[0]
    if isinstance(payload, dict):
        return payload
    return {}


def get_single_row(table: str, *, filters: Dict[str, str]) -> Optional[Dict[str, Any]]:
    url = _table_url(table)
    headers = _base_headers()
    params = {k: f"eq.{v}" for k, v in filters.items()}
    params["limit"] = "1"
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    try:
        resp.raise_for_status()
    except Exception:
        logger.exception("Failed to fetch from %s: %s", table, resp.text)
        raise
    data = resp.json()
    if isinstance(data, list) and data:
        return data[0]
    return None


def log_activity(pql_id: Optional[str], action: str, details: Optional[Dict[str, Any]] = None) -> None:
    payload: Dict[str, Any] = {
        "action": action,
    }
    if pql_id is not None:
        payload["pql_id"] = pql_id
    if details is not None:
        payload["details"] = details
    insert_row("activity_log", payload)


