"""Analyzer 데이터 모델(Analyzer data models)."""
from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class AnalyzerInput(BaseModel):
    """분석 입력 모델(Analysis input model)."""

    cve_id: str = Field(..., description="CVE 식별자")
    epss_score: float = Field(..., ge=0.0, le=1.0, description="EPSS 점수")
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

