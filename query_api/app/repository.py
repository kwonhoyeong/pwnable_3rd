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

        # SQLite용: json_each를 사용하여 JSON 배열을 제대로 확장
        query = text(
            """
            SELECT
                json_extract(cve.value, '$') AS cve_id,
                COALESCE(es.epss_score, 0.0) AS epss_score,
                cs.cvss_score,
                ar.risk_level,
                ar.analysis_summary,
                ar.recommendations
            FROM package_cve_mapping pcm,
                 json_each(pcm.cve_ids) AS cve
            LEFT JOIN epss_scores es ON es.cve_id = json_extract(cve.value, '$')
            LEFT JOIN cvss_scores cs ON cs.cve_id = json_extract(cve.value, '$')
            LEFT JOIN analysis_results ar ON ar.cve_id = json_extract(cve.value, '$')
            WHERE pcm.package = :package
            """
        )
        result = await self._session.execute(query, {"package": package})
        rows = result.fetchall()

        import json
        return [
            {
                "cve_id": row.cve_id.strip('"') if isinstance(row.cve_id, str) else row.cve_id,
                "epss_score": row.epss_score or 0.0,
                "cvss_score": row.cvss_score,
                "risk_level": row.risk_level or "Unknown",
                "analysis_summary": row.analysis_summary or "",
                "recommendations": json.loads(row.recommendations) if isinstance(row.recommendations, str) else (row.recommendations or []),
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

        import json
        return [
            {
                "cve_id": row.cve_id,
                "epss_score": row.epss_score or 0.0,
                "cvss_score": row.cvss_score,
                "risk_level": row.risk_level or "Unknown",
                "analysis_summary": row.analysis_summary or "",
                "recommendations": json.loads(row.recommendations) if isinstance(row.recommendations, str) else (row.recommendations or []),
            }
            for row in rows
        ]

