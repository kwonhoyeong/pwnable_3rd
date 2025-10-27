"""ThreatAgent 데이터 저장소(ThreatAgent data repository)."""
from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common_lib.logger import get_logger

logger = get_logger(__name__)


class ThreatRepository:
    """위협 사례 저장 레이어(Storage layer for threat cases)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_cases(
        self, cve_id: str, package: str, version_range: str, cases: List[dict[str, object]]
    ) -> None:
        """사례 정보를 저장/갱신(Store or update collected cases)."""

        query = text(
            """
            INSERT INTO threat_cases (cve_id, package, version_range, cases)
            VALUES (:cve_id, :package, :version_range, :cases)
            ON CONFLICT (cve_id, package, version_range)
            DO UPDATE SET cases = EXCLUDED.cases, updated_at = NOW()
            """
        )
        await self._session.execute(
            query,
            {
                "cve_id": cve_id,
                "package": package,
                "version_range": version_range,
                "cases": cases,
            },
        )

    async def is_duplicate(self, cve_id: str, source: str) -> bool:
        """중복 여부 검사(Check duplication)."""

        query = text(
            """
            SELECT 1 FROM threat_cases, jsonb_array_elements(threat_cases.cases) AS case
            WHERE threat_cases.cve_id = :cve_id AND case->>'source' = :source LIMIT 1
            """
        )
        result = await self._session.execute(query, {"cve_id": cve_id, "source": source})
        return result.first() is not None

