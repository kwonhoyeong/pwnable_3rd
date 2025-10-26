"""CVSS 데이터 저장소(CVSS data repository)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common_lib.logger import get_logger

logger = get_logger(__name__)


class CVSSRepository:
    """CVSS 점수 저장 레이어(Storage layer for CVSS scores)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_score(self, cve_id: str, cvss_score: float, vector: str | None, collected_at: datetime) -> None:
        """CVSS 점수 저장 또는 갱신(Upsert CVSS score)."""

        query = text(
            """
            INSERT INTO cvss_scores (cve_id, cvss_score, vector, collected_at)
            VALUES (:cve_id, :cvss_score, :vector, :collected_at)
            ON CONFLICT (cve_id)
            DO UPDATE SET cvss_score = EXCLUDED.cvss_score, vector = EXCLUDED.vector, collected_at = EXCLUDED.collected_at
            """
        )
        await self._session.execute(
            query,
            {
                "cve_id": cve_id,
                "cvss_score": cvss_score,
                "vector": vector,
                "collected_at": collected_at,
            },
        )
