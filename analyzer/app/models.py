"""Analyzer 데이터 모델(Analyzer data models)."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AnalyzerInput(BaseModel):
    """분석 입력 모델(Analysis input model)."""

    cve_id: str = Field(..., description="CVE 식별자")
    epss_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="EPSS 점수 (없으면 None)")
    cvss_score: Optional[float] = Field(None, ge=0.0, le=10.0, description="CVSS 기본 점수 (없으면 None)")
    cases: List[dict] = Field(default_factory=list, description="위협 사례 목록")
    package: str = Field(..., description="패키지 이름")
    version_range: str = Field(..., description="버전 범위")


class AnalyzerOutput(BaseModel):
    """분석 결과 모델(Analysis output model)."""

    cve_id: str
    risk_level: str
    recommendations: List[str]
    analysis_summary: str
    generated_at: datetime

