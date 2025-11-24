"""QueryAPI 데이터 모델(QueryAPI data models)."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class CVEDetail(BaseModel):
    """CVE 상세 정보 모델(CVE detail model).

    Represents a single CVE's vulnerability analysis with calculated priority metrics.

    NOTE: Distinction between database storage and API response
        - database analysis_results table stores: cve_id, risk_level, risk_score, analysis_summary, recommendations
        - API response ADDS calculated fields: risk_score, risk_label (NOT in raw database)
        - Service layer (_prioritize method) calculates these metrics from risk_level + cvss_score + epss_score

    Fields:
        cve_id: CVE identifier (e.g., "CVE-2024-1234")
        epss_score: Exploit Prediction Scoring System score (0-1), null if unavailable.
                   Retrieved from epss_scores table via CVE join.
        cvss_score: Common Vulnerability Scoring System score (0-10), null if unavailable.
                   Retrieved from cvss_scores table via CVE join.
        risk_level: Human-readable risk level (CRITICAL, HIGH, MEDIUM, LOW, Unknown).
                   Retrieved from analysis_results table.
        analysis_summary: Detailed analysis text (may be in Markdown format).
                         Retrieved from analysis_results table.
        recommendations: List of recommended mitigation steps.
                        Retrieved from analysis_results table.
        risk_score: AI-calculated risk score.
                       Retrieved from analysis_results table via CVE join.
        risk_label: Human-readable risk label (P1, P2, P3).
                       Derived from risk_score by service layer.
                       P1: Score >= 80.0
                       P2: Score >= 50.0
                       P3: Score < 50.0
    """

    cve_id: str
    epss_score: float | None = None
    cvss_score: float | None = None
    risk_level: str
    analysis_summary: str
    recommendations: List[str]
    risk_score: float  # Retrieved from database
    risk_label: str  # Derived from risk_score by service layer


class QueryResponse(BaseModel):
    """쿼리 응답 모델(Query response model)."""

    package: Optional[str] = None
    cve_id: Optional[str] = None
    cve_list: List[CVEDetail]
