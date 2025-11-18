"""EPSS 데이터 모델(EPSS data models)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EPSSInput(BaseModel):
    """EPSS 조회 입력 모델(Input model for EPSS lookups)."""

    cve_id: str = Field(..., description="CVE 식별자(CVE identifier)")


class EPSSRecord(BaseModel):
    """EPSS 결과 모델(Result model for EPSS)."""

    cve_id: str
    epss_score: float | None = None
    source: str | None = None
    collected_at: datetime
