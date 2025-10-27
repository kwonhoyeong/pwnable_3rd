"""QueryAPI 데이터 접근 계층(QueryAPI data access layer)."""
from __future__ import annotations

from typing import List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common_lib.logger import get_logger

logger = get_logger(__name__)


class QueryRepository:
    """복합 조회용 저장소(Repository for aggregated lookups)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_package(self, package: str) -> List[dict[str, object]]:
        """패키지로 조회(Look up by package)."""

        query = text(
            """
            WITH expanded AS (
                SELECT package, version_range, UNNEST(cve_ids) AS cve_id
                FROM package_cve_mapping
                WHERE package = :package
            )
            SELECT exp.cve_id,
                   COALESCE(es.epss_score, 0.0) AS epss_score,
                   cs.cvss_score,
                   ar.risk_level,
                   ar.analysis_summary,
                   ar.recommendations
            FROM expanded exp
            LEFT JOIN epss_scores es ON es.cve_id = exp.cve_id
            LEFT JOIN cvss_scores cs ON cs.cve_id = exp.cve_id
            LEFT JOIN analysis_results ar ON ar.cve_id = exp.cve_id
            """
        )
        result = await self._session.execute(query, {"package": package})
        rows = result.fetchall()
        return [
            {
                "cve_id": row.cve_id,
                "epss_score": row.epss_score or 0.0,
                "cvss_score": row.cvss_score,
                "risk_level": row.risk_level or "Unknown",
                "analysis_summary": row.analysis_summary or "",
                "recommendations": row.recommendations or [],
            }
            for row in rows
        ]

    async def find_by_cve(self, cve_id: str) -> List[dict[str, object]]:
        """CVE로 조회(Look up by CVE)."""

        query = text(
            """
            SELECT ar.cve_id,
                   es.epss_score,
                   cs.cvss_score,
                   ar.risk_level,
                   ar.analysis_summary,
                   ar.recommendations
            FROM analysis_results ar
            LEFT JOIN epss_scores es ON es.cve_id = ar.cve_id
            LEFT JOIN cvss_scores cs ON cs.cve_id = ar.cve_id
            WHERE ar.cve_id = :cve_id
            """
        )
        result = await self._session.execute(query, {"cve_id": cve_id})
        rows = result.fetchall()
        return [
            {
                "cve_id": row.cve_id,
                "epss_score": row.epss_score or 0.0,
                "cvss_score": row.cvss_score,
                "risk_level": row.risk_level or "Unknown",
                "analysis_summary": row.analysis_summary or "",
                "recommendations": row.recommendations or [],
            }
            for row in rows
        ]

