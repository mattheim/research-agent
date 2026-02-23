from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class PqlRecordIn(BaseModel):
    id: str
    email: str
    company_name: Optional[str] = None
    product_usage_score: Optional[float] = None
    last_active_date: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    status: str

    class Config:
        extra = "allow"


class ResearchResult(BaseModel):
    pql_id: str
    company_info: Dict[str, Any]
    key_contacts: List[Dict[str, Any]]
    research_source: str


class ResearchRequest(BaseModel):
    qualification_threshold: Optional[int] = None
