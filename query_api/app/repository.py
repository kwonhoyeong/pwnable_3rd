"""QueryAPI 데이터 접근 계층(QueryAPI data access layer)."""
from __future__ import annotations

from typing import Dict, List

from sqlalchemy import desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from common_lib.errors import ExternalServiceError, ResourceNotFound
from common_lib.logger import get_logger

logger = get_logger(__name__)


class QueryRepository:
    """복합 조회용 저장소(Repository for aggregated lookups)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_package(self, package: str, ecosystem: str = "npm", version: str | None = None) -> List[dict[str, object]]:
        """패키지로 조회(Look up by package).

        Args:
            package: Package name to search for
            ecosystem: Package ecosystem (npm, pip, apt)
            version: Optional package version. If provided, filters CVEs by version_range.
                    If None, returns all CVEs for the package.
        """

        # Build WHERE clause with ecosystem filtering
        where_clause = "WHERE package = :package AND ecosystem = :ecosystem"
        params: dict[str, object] = {"package": package, "ecosystem": ecosystem}

        if version:
            where_clause += " AND version_range = :version"
            params["version"] = version

        query = text(
            f"""
            WITH expanded AS (
                SELECT package, version_range, UNNEST(cve_ids) AS cve_id
                FROM package_cve_mapping
                {where_clause}
            )
            SELECT exp.cve_id,
                   es.epss_score,
                   cs.cvss_score,
                   ar.risk_level,
                   ar.risk_score,
                   ar.analysis_summary,
                   ar.recommendations
            FROM expanded exp
            LEFT JOIN epss_scores es ON es.cve_id = exp.cve_id
            LEFT JOIN cvss_scores cs ON cs.cve_id = exp.cve_id
            LEFT JOIN analysis_results ar ON ar.cve_id = exp.cve_id
            """
        )
        try:
            result = await self._session.execute(query, params)
            rows = result.fetchall()

            if not rows:
                raise ResourceNotFound(
                    resource_type="package",
                    identifier=package,
                    details={"reason": "No CVEs found for this package"},
                )

            return [
                {
                    "cve_id": row.cve_id,
                    "epss_score": float(row.epss_score) if row.epss_score is not None else None,
                    "cvss_score": float(row.cvss_score) if row.cvss_score is not None else None,
                    "risk_level": row.risk_level or "Unknown",
                    "risk_score": float(row.risk_score) if hasattr(row, "risk_score") and row.risk_score is not None else 0.0,
                    "analysis_summary": row.analysis_summary or "",
                    "recommendations": row.recommendations or [],
                }
                for row in rows
            ]
        except ResourceNotFound:
            raise
        except Exception as exc:
            logger.error("Database error in find_by_package: %s", exc, exc_info=exc)
            raise ExternalServiceError(
                service_name="Database",
                reason="Failed to query package data",
                details={"package": package},
            ) from exc

    async def find_by_cve(self, cve_id: str) -> List[dict[str, object]]:
        """CVE로 조회(Look up by CVE)."""

        query = text(
            """
            SELECT ar.cve_id,
                   es.epss_score,
                   cs.cvss_score,
                   ar.risk_level,
                   ar.risk_score,
                   ar.analysis_summary,
                   ar.recommendations
            FROM analysis_results ar
            LEFT JOIN epss_scores es ON es.cve_id = ar.cve_id
            LEFT JOIN cvss_scores cs ON cs.cve_id = ar.cve_id
            WHERE ar.cve_id = :cve_id
            """
        )
        try:
            result = await self._session.execute(query, {"cve_id": cve_id})
            rows = result.fetchall()

            if not rows:
                raise ResourceNotFound(
                    resource_type="CVE",
                    identifier=cve_id,
                    details={"reason": "No analysis found for this CVE"},
                )

            return [
                {
                    "cve_id": row.cve_id,
                    "epss_score": float(row.epss_score) if row.epss_score is not None else None,
                    "cvss_score": float(row.cvss_score) if row.cvss_score is not None else None,
                    "risk_level": row.risk_level or "Unknown",
                    "risk_score": float(row.risk_score) if hasattr(row, "risk_score") and row.risk_score is not None else 0.0,
                    "analysis_summary": row.analysis_summary or "",
                    "recommendations": row.recommendations or [],
                }
                for row in rows
            ]
        except ResourceNotFound:
            raise
        except Exception as exc:
            logger.error("Database error in find_by_cve: %s", exc, exc_info=exc)
            raise ExternalServiceError(
                service_name="Database",
                reason="Failed to query CVE data",
                details={"cve_id": cve_id},
            ) from exc

    async def get_history(self, skip: int = 0, limit: int = 10) -> List[dict[str, object]]:
        """분석 히스토리 조회(Fetch analysis history with pagination)."""

        query = text(
            """
            SELECT ar.cve_id,
                   ar.risk_level,
                   ar.risk_score,
                   ar.analysis_summary,
                   ar.recommendations,
                   ar.generated_at,
                   ar.created_at
            FROM analysis_results ar
            ORDER BY ar.created_at DESC
            LIMIT :limit OFFSET :skip
            """
        )
        result = await self._session.execute(query, {"skip": skip, "limit": limit})
        rows = result.fetchall()
        return [
            {
                "cve_id": row.cve_id,
                "risk_level": row.risk_level,
                "risk_score": float(row.risk_score) if hasattr(row, "risk_score") and row.risk_score is not None else None,
                "analysis_summary": row.analysis_summary or "",
                "recommendations": row.recommendations or [],
                "generated_at": row.generated_at.isoformat() if row.generated_at else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

    async def get_risk_stats(self) -> Dict[str, int]:
        """위험도 통계 조회(Get risk distribution statistics)."""

        query = text(
            """
            SELECT risk_level, COUNT(*) as count
            FROM analysis_results
            WHERE risk_level IS NOT NULL
            GROUP BY risk_level
            ORDER BY risk_level
            """
        )
        result = await self._session.execute(query)
        rows = result.fetchall()

        # Initialize with all possible risk levels (UPPERCASE to match normalization)
        stats = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "UNKNOWN": 0,  # Changed from "Unknown" to "UNKNOWN"
        }

        # Update with actual data
        try:
            for row in rows:
                # Normalize to uppercase for consistent key lookup
                risk_level = (row.risk_level or "UNKNOWN").upper()
                
                # Fallback: if unexpected severity, map to UNKNOWN instead of crashing
                if risk_level not in stats:
                    logger.warning("Unexpected risk_level '%s' found, mapping to UNKNOWN", risk_level)
                    risk_level = "UNKNOWN"
                
                stats[risk_level] = row.count
        except Exception as exc:
            logger.error("Error aggregating risk stats: %s", exc, exc_info=True)
            # Return initialized stats on error instead of crashing

        return stats

    async def delete_by_package(self, package: str, ecosystem: str = "npm", version: str | None = None) -> None:
        """패키지 데이터 삭제(Delete package data).
        
        Args:
            package: Package name to delete
            ecosystem: Package ecosystem (npm, pip, apt)
            version: Optional package version. If provided, only deletes this specific version.
                    If None, deletes all versions of the package.
        """
        try:
            # Build WHERE clause with optional version filtering
            where_clause = "WHERE package = :package AND ecosystem = :ecosystem"
            params: dict[str, object] = {"package": package, "ecosystem": ecosystem}
            
            if version:
                where_clause += " AND version_range = :version"
                params["version"] = version
            
            query = text(f"DELETE FROM package_cve_mapping {where_clause}")
            await self._session.execute(query, params)
            await self._session.commit()
            
            if version:
                logger.info("Deleted package data for %s@%s (ecosystem=%s)", package, version, ecosystem)
            else:
                logger.info("Deleted all versions of package %s (ecosystem=%s)", package, ecosystem)
        except Exception as exc:
            logger.error("Database error in delete_by_package: %s", exc, exc_info=exc)
            raise ExternalServiceError(
                service_name="Database",
                reason="Failed to delete package data",
                details={"package": package, "version": version},
            ) from exc

    async def delete_by_cve(self, cve_id: str) -> None:
        """CVE 분석 결과 삭제(Delete CVE analysis results)."""
        try:
            # Delete from analysis_results, epss_scores, and cvss_scores
            queries = [
                text("DELETE FROM analysis_results WHERE cve_id = :cve_id"),
                text("DELETE FROM epss_scores WHERE cve_id = :cve_id"),
                text("DELETE FROM cvss_scores WHERE cve_id = :cve_id"),
            ]
            for query in queries:
                await self._session.execute(query, {"cve_id": cve_id})
            await self._session.commit()
            logger.info("Deleted existing analysis data for CVE %s", cve_id)
        except Exception as exc:
            logger.error("Database error in delete_by_cve: %s", exc, exc_info=exc)
            raise ExternalServiceError(
                service_name="Database",
                reason="Failed to delete CVE data",
                details={"cve_id": cve_id},
            ) from exc
