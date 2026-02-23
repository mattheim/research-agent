from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, List
from urllib.parse import urlparse

import requests

from .config import GOOGLE_SEARCH_API_KEY, GOOGLE_SEARCH_CX

try:
    from playwright.async_api import Error as PlaywrightError
    from playwright.async_api import TimeoutError as PlaywrightTimeoutError
    from playwright.async_api import async_playwright
except Exception:  # pragma: no cover - optional dependency guard
    PlaywrightError = Exception
    PlaywrightTimeoutError = Exception
    async_playwright = None

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT_SECONDS = 8
PLAYWRIGHT_TIMEOUT_MS = 10_000
MAX_TEXT_CHARS = 700


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"\s+", " ", value)
    return cleaned.strip()


def _truncate(value: str, max_chars: int = MAX_TEXT_CHARS) -> str:
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 1].rstrip() + "…"


def _normalize_url(url: str | None) -> str | None:
    if not url:
        return None
    candidate = url.strip()
    if not candidate:
        return None
    if not candidate.startswith(("http://", "https://")):
        candidate = f"https://{candidate}"

    parsed = urlparse(candidate)
    if not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path or ''}"


def _extract_title(html_content: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html_content, flags=re.IGNORECASE | re.DOTALL)
    return _clean_text(match.group(1)) if match else ""


def _extract_meta_description(html_content: str) -> str:
    match = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']',
        html_content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return _clean_text(match.group(1)) if match else ""


def _extract_visible_excerpt(html_content: str) -> str:
    no_script = re.sub(
        r"<script[\\s\\S]*?</script>|<style[\\s\\S]*?</style>",
        " ",
        html_content,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"<[^>]+>", " ", no_script)
    return _truncate(_clean_text(text))


def _fetch_page_summary_requests(url: str) -> Dict[str, Any]:
    try:
        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
            allow_redirects=True,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        return {
            "url": url,
            "ok": False,
            "error": str(exc),
            "renderer": "requests",
        }

    content_type = (response.headers.get("Content-Type") or "").lower()
    if "text/html" not in content_type:
        return {
            "url": response.url,
            "ok": True,
            "title": "",
            "description": "",
            "excerpt": "",
            "content_type": content_type,
            "renderer": "requests",
        }

    html_content = response.text or ""
    return {
        "url": response.url,
        "ok": True,
        "title": _extract_title(html_content),
        "description": _extract_meta_description(html_content),
        "excerpt": _extract_visible_excerpt(html_content),
        "content_type": content_type,
        "renderer": "requests",
    }


async def _fetch_page_summary_playwright(url: str) -> Dict[str, Any]:
    if async_playwright is None:
        return {
            "url": url,
            "ok": False,
            "error": "Playwright is not installed. Install with `pip install playwright` and `playwright install chromium`.",
            "renderer": "playwright",
        }

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=USER_AGENT, ignore_https_errors=True)
            page = await context.new_page()

            response = await page.goto(url, wait_until="domcontentloaded", timeout=PLAYWRIGHT_TIMEOUT_MS)
            await page.wait_for_timeout(400)

            content_type = ""
            if response is not None:
                content_type = (response.headers.get("content-type") or "").lower()

            final_url = page.url
            html_content = await page.content()
            title = _clean_text(await page.title())

            description = _clean_text(
                await page.locator("meta[name='description']").first.get_attribute("content")
            )
            if not description:
                description = _extract_meta_description(html_content)

            body_text = await page.evaluate(
                """
                () => {
                  const body = document.body;
                  if (!body) return "";
                  return body.innerText || "";
                }
                """
            )

            excerpt = _truncate(_clean_text(body_text)) if body_text else _extract_visible_excerpt(html_content)

            await context.close()
            await browser.close()

            return {
                "url": final_url,
                "ok": True,
                "title": title,
                "description": description,
                "excerpt": excerpt,
                "content_type": content_type,
                "renderer": "playwright",
            }
    except (PlaywrightTimeoutError, PlaywrightError) as exc:
        return {
            "url": url,
            "ok": False,
            "error": str(exc),
            "renderer": "playwright",
        }


async def _fetch_page_summary_async(url: str) -> Dict[str, Any]:
    playwright_result = await _fetch_page_summary_playwright(url)
    if playwright_result.get("ok"):
        return playwright_result

    fallback = await asyncio.to_thread(_fetch_page_summary_requests, url)
    fallback["playwright_error"] = playwright_result.get("error")
    if fallback.get("renderer") == "requests":
        fallback["renderer"] = "requests_fallback"
    return fallback



def _extract_google_api_error(payload: Dict[str, Any], http_status: int) -> Dict[str, Any]:
    error_obj = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(error_obj, dict):
        return {
            "http_status": http_status,
            "message": "Google Custom Search API returned an error.",
            "reasons": [],
        }

    message = _clean_text(str(error_obj.get("message") or ""))
    status = _clean_text(str(error_obj.get("status") or ""))
    reasons: List[str] = []

    details = error_obj.get("errors")
    if isinstance(details, list):
        for item in details:
            if not isinstance(item, dict):
                continue
            reason = _clean_text(str(item.get("reason") or ""))
            if reason:
                reasons.append(reason)

    out: Dict[str, Any] = {
        "http_status": http_status,
        "message": message or "Google Custom Search API returned an error.",
        "reasons": reasons,
    }
    if status:
        out["status"] = status
    return out


def _search_subject_google_api(subject: str, limit: int = 5) -> Dict[str, Any]:
    query = _clean_text(subject)
    if not query:
        return {"query": "", "engine": "google", "results": []}

    if not GOOGLE_SEARCH_API_KEY or not GOOGLE_SEARCH_CX:
        return {
            "query": query,
            "engine": "google",
            "results": [],
            "error": "GOOGLE_SEARCH_API_KEY/GOOGLE_SEARCH_CX not configured.",
            "google_error": {
                "http_status": 400,
                "message": "Missing required Google Custom Search credentials.",
                "reasons": ["missing_api_credentials"],
            },
        }

    try:
        response = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": GOOGLE_SEARCH_API_KEY,
                "cx": GOOGLE_SEARCH_CX,
                "q": query,
                "num": max(1, min(limit, 10)),
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
        )
    except requests.RequestException:
        return {
            "query": query,
            "engine": "google",
            "results": [],
            "error": "Google Custom Search API request failed.",
            "google_error": {
                "http_status": 503,
                "message": "Network request to Google Custom Search API failed.",
                "reasons": ["network_request_failed"],
            },
        }

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    if response.status_code >= 400:
        google_error = _extract_google_api_error(payload, response.status_code)
        return {
            "query": query,
            "engine": "google",
            "results": [],
            "error": f"Google Custom Search API error (HTTP {response.status_code}).",
            "google_error": google_error,
            "renderer": "google_custom_search_api",
        }

    items = payload.get("items") if isinstance(payload, dict) else None
    results: List[Dict[str, str]] = []
    if isinstance(items, list):
        for item in items[: max(1, min(limit, 10))]:
            link = _clean_text(str(item.get("link") or ""))
            title = _clean_text(str(item.get("title") or ""))
            snippet = _clean_text(str(item.get("snippet") or ""))
            if not link:
                continue
            results.append(
                {
                    "title": title,
                    "url": link,
                    "snippet": _truncate(snippet) if snippet else "",
                }
            )

    return {
        "query": query,
        "engine": "google",
        "results": results,
        "renderer": "google_custom_search_api",
    }


async def _search_subject_async(subject: str, limit: int = 5) -> Dict[str, Any]:
    return await asyncio.to_thread(_search_subject_google_api, subject, limit)


def _build_sources(website: Dict[str, Any] | None, search: Dict[str, Any]) -> List[str]:
    sources: List[str] = []
    if website and website.get("url"):
        sources.append(str(website["url"]))
    for row in search.get("results", []):
        if row.get("url"):
            sources.append(row["url"])

    seen = set()
    ordered_sources: List[str] = []
    for source in sources:
        if source in seen:
            continue
        seen.add(source)
        ordered_sources.append(source)
    return ordered_sources


def gather_subject_context(subject: str, website_hint_url: str | None = None) -> Dict[str, Any]:
    """
    Synchronous web navigation context for a subject.

    Uses requests-based website fetching + Google Custom Search API for search.
    """
    normalized_url = _normalize_url(website_hint_url)
    website = _fetch_page_summary_requests(normalized_url) if normalized_url else None
    search = _search_subject_google_api(subject, limit=5)

    return {
        "subject": _clean_text(subject),
        "website": website,
        "search": search,
        "sources": _build_sources(website, search),
    }


async def gather_subject_context_async(subject: str, website_hint_url: str | None = None) -> Dict[str, Any]:
    normalized_url = _normalize_url(website_hint_url)
    website = await _fetch_page_summary_async(normalized_url) if normalized_url else None
    search = await _search_subject_async(subject, limit=5)

    return {
        "subject": _clean_text(subject),
        "website": website,
        "search": search,
        "sources": _build_sources(website, search),
    }


async def google_search_top_links_async(query: str, limit: int = 5) -> Dict[str, Any]:
    """
    Return top links from Google Custom Search JSON API for a free-text query.

    Requires GOOGLE_SEARCH_API_KEY and GOOGLE_SEARCH_CX in env.
    """
    sanitized_query = _clean_text(query)
    if not sanitized_query:
        return {"query": "", "engine": "google", "links": []}

    sanitized_limit = max(1, min(limit, 10))
    search = await _search_subject_async(sanitized_query, limit=sanitized_limit)

    links: List[str] = []
    seen: set[str] = set()
    for result in search.get("results", []):
        url = _clean_text(str(result.get("url") or ""))
        if not url or url in seen:
            continue
        seen.add(url)
        links.append(url)
        if len(links) >= sanitized_limit:
            break

    payload: Dict[str, Any] = {
        "query": sanitized_query,
        "engine": "google",
        "links": links,
        "source": "google_custom_search_api",
    }

    if "renderer" in search:
        payload["renderer"] = search.get("renderer")
    if "error" in search:
        payload["error"] = search.get("error")
    if "google_error" in search:
        payload["google_error"] = search.get("google_error")

    return payload
