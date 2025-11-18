"""QueryAPI 데이터 모델(QueryAPI data models)."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class CVEDetail(BaseModel):
    """CVE 상세 정보 모델(CVE detail model)."""

    cve_id: str
    epss_score: float | None = None
    cvss_score: float | None = None
    risk_level: str
    analysis_summary: str
    recommendations: List[str]
    priority_score: float
    priority_label: str


class QueryResponse(BaseModel):
    """쿼리 응답 모델(Query response model)."""

    package: Optional[str] = None
    cve_id: Optional[str] = None
    cve_list: List[CVEDetail]
