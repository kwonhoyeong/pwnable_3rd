"""CVSSFetcher 데이터 모델(CVSSFetcher data models)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CVSSInput(BaseModel):
    """CVSS 조회 입력 모델(Input model for CVSS lookup)."""

    cve_id: str = Field(..., description="CVE 식별자(CVE identifier)")


class CVSSRecord(BaseModel):
    """CVSS 응답 모델(Response model for CVSS data)."""

    cve_id: str
    cvss_score: float
    vector: str | None = None
    collected_at: datetime
