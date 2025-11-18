"""EPSS 데이터 저장소(EPSS data repository)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common_lib.logger import get_logger

logger = get_logger(__name__)


class EPSSRepository:
    """EPSS 점수 저장/조회 레이어(Storage layer for EPSS scores)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_score(self, cve_id: str, epss_score: float | None, collected_at: datetime) -> None:
        """EPSS 점수 저장(Upsert EPSS score)."""

        query = text(
            """
            INSERT INTO epss_scores (cve_id, epss_score, collected_at)
            VALUES (:cve_id, :epss_score, :collected_at)
            ON CONFLICT (cve_id)
            DO UPDATE SET epss_score = EXCLUDED.epss_score, collected_at = EXCLUDED.collected_at
            """
        )
        await self._session.execute(
            query,
            {"cve_id": cve_id, "epss_score": epss_score, "collected_at": collected_at},
        )
