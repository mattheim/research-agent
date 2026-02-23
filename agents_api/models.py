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


class QualificationLLMOutput(BaseModel):
    """
    Minimal normalization output from the LLM.

    We only allow the model to interpret how many days have passed
    since the last_active value; all qualification decisions are
    deterministic rules in code.
    """

    days_since_last_active: int | None = None


class QualificationResult(BaseModel):
    id: str
    qualification_result: str
    agent_metadata: Dict[str, Any]
    status: Optional[str] = None


class QualifyRequest(BaseModel):
    pqls: List[PqlRecordIn]
    qualification_threshold: Optional[int] = None


class QualifyResponse(BaseModel):
    qualified: List[QualificationResult]


class EnrichmentResult(BaseModel):
    pql_id: str
    company_info: Dict[str, Any]
    key_contacts: List[Dict[str, Any]]
    enrichment_source: str


class EmailDraftResult(BaseModel):
    pql_id: str
    to_email: str
    subject: str
    body: str
    proposed_offer: str
    ai_reasoning: str


class RegenerateEmailRequest(BaseModel):
    override_context: Optional[Dict[str, Any]] = None


class EnrichRequest(BaseModel):
    qualification_threshold: Optional[int] = None
