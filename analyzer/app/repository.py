"""Analyzer 데이터 접근 계층(Analyzer data access layer)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common_lib.logger import get_logger

logger = get_logger(__name__)


class AnalysisRepository:
    """분석 결과 저장 레이어(Storage layer for analysis results)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_analysis(
        self,
        cve_id: str,
        risk_level: str,
        risk_score: float,
        recommendations: list[str],
        analysis_summary: str,
        generated_at: datetime,
    ) -> None:
        """분석 결과 저장(Upsert analysis result)."""

        query = text(
            """
            INSERT INTO analysis_results (cve_id, risk_level, risk_score, recommendations, analysis_summary, generated_at)
            VALUES (:cve_id, :risk_level, :risk_score, :recommendations, :analysis_summary, :generated_at)
            ON CONFLICT (cve_id)
            DO UPDATE SET risk_level = EXCLUDED.risk_level,
                          risk_score = EXCLUDED.risk_score,
                          recommendations = EXCLUDED.recommendations,
                          analysis_summary = EXCLUDED.analysis_summary,
                          generated_at = EXCLUDED.generated_at
            """
        )
        await self._session.execute(
            query,
            {
                "cve_id": cve_id,
                "risk_level": risk_level,
                "risk_score": risk_score,
                "recommendations": recommendations,
                "analysis_summary": analysis_summary,
                "generated_at": generated_at,
            },
        )

