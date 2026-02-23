import re
from typing import Any, Dict


PERSONAL_EMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "yahoo.com",
    "yahoo.co.uk",
    "outlook.com",
    "hotmail.com",
    "live.com",
    "msn.com",
    "icloud.com",
    "me.com",
    "aol.com",
    "proton.me",
    "protonmail.com",
    "mail.com",
    "gmx.com",
    "ymail.com",
}


def _normalize_company_name(company_name: str | None) -> str:
    if not company_name:
        return ""
    return re.sub(r"[^a-z0-9]", "", company_name.lower())


def _extract_email_domain(email: str | None) -> str:
    if not email or "@" not in email:
        return ""
    domain = email.split("@", 1)[1].strip().lower()
    if not domain or "." not in domain:
        return ""
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def infer_website_hint(email: str | None, company_name: str | None) -> Dict[str, Any]:
    """
    Infer a likely homepage URL without performing any web requests.

    Priority:
    1) Business email domain
    2) Normalized company name + .com
    """
    domain = _extract_email_domain(email)
    if domain and domain not in PERSONAL_EMAIL_DOMAINS:
        return {"url": f"https://{domain}", "source": "email_domain"}

    normalized_company = _normalize_company_name(company_name)
    if normalized_company:
        return {"url": f"https://{normalized_company}.com", "source": "company_name_com"}

    return {"url": None, "source": "none"}
