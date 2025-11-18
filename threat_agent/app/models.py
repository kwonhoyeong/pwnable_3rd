"""ThreatAgent 데이터 모델(ThreatAgent data models)."""
from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class ThreatInput(BaseModel):
    """위협 정보 입력 모델(Threat information input model)."""

    cve_id: str = Field(..., description="CVE 식별자(CVE identifier)")
    package: str = Field(..., description="패키지 이름(Package name)")
    version_range: str = Field(..., description="버전 범위(Version range)")


class ThreatCase(BaseModel):
    """공격 사례 모델(Attack case model)."""

    source: str = Field(..., description="위협 사례 출처 URL(Source URL of threat case)")
    title: str
    date: str
    summary: str
    collected_at: datetime


class ThreatResponse(BaseModel):
    """위협 수집 결과 모델(Threat collection result)."""

    cve_id: str
    package: str
    version_range: str
    cases: List[ThreatCase]

