"""QueryAPI 서비스 레이어(QueryAPI service layer)."""
from __future__ import annotations

import asyncio
import json
from typing import List, Optional

from common_lib.cache import get_redis
from common_lib.errors import AnalysisInProgressError, ExternalServiceError, InvalidInputError, ResourceNotFound
from common_lib.logger import get_logger

from .models import CVEDetail, QueryResponse
from .repository import QueryRepository
from .redis_ops import submit_analysis_job

logger = get_logger(__name__)

# Analysis trigger and wait configuration
ANALYSIS_POLL_INTERVAL = 2.0  # seconds between polls
ANALYSIS_MAX_WAIT_TIME = 120.0  # total seconds to wait for results


class QueryService:
    """쿼리 처리 서비스(Query handling service)."""

    def __init__(self, cache_ttl: int = 300) -> None:
        self._cache_ttl = cache_ttl

    async def query(
        self,
        repository: QueryRepository,
        package: Optional[str],
        cve_id: Optional[str],
        version: Optional[str] = None,
        ecosystem: str = "npm",
        force: bool = False,
    ) -> QueryResponse:
        """패키지 또는 CVE 기준으로 조회(Query by package or CVE).

        Args:
            repository: Query repository for database access
            package: Package name to search for
            cve_id: CVE ID to search for
            version: Optional package version. If not provided, defaults to 'latest' for analysis jobs.
            ecosystem: Package ecosystem (default: "npm")

        If data is not found, triggers analysis and polls for results.
        """

        cache_key = self._build_cache_key(package, cve_id, version, ecosystem)
        redis = None
        try:
            redis = await get_redis()
            cached = await redis.get(cache_key)
        except Exception as exc:  # pragma: no cover - cache fallback
            cached = None
            logger.warning("Redis unavailable, bypassing cache", exc_info=exc)
        if cached and not force:
            logger.debug("Cache hit for %s", cache_key)
            return QueryResponse(**json.loads(cached))


        # If force is True, skip database check and trigger re-analysis
        if force:
            logger.info(
                "Force flag set. Skipping cache/DB check and triggering re-analysis for %s (ecosystem=%s)",
                package or cve_id,
                ecosystem,
            )
            
            # Delete existing data first (only the specific version if provided)
            if package:
                await repository.delete_by_package(package, ecosystem, version)
            elif cve_id:
                await repository.delete_by_cve(cve_id)
            
            # Submit analysis job to Redis
            if package:
                success = await submit_analysis_job(
                    package_name=package,
                    version=version or "latest",
                    force=force,
                    source="web_query",
                    ecosystem=ecosystem,
                )
            else:
                success = await submit_analysis_job(
                    cve_id=cve_id,
                    force=force,
                    source="web_query_cve_only",
                    ecosystem=ecosystem,
                )

            if not success:
                logger.warning("Failed to submit analysis job for %s", package or cve_id)
                raise ExternalServiceError(
                    service_name="Redis",
                    reason="Failed to submit analysis job",
                )

            # Poll database for results
            results = await self._poll_for_analysis_results(
                repository, package, cve_id, version, ecosystem
            )

            if results is not None:
                response = results
            else:
                # Timeout - analysis still in progress
                resource_type = "package" if package else "cve"
                identifier = package or cve_id or "unknown"
                raise AnalysisInProgressError(
                    resource_type=resource_type,
                    identifier=identifier,
                    details={
                        "wait_time": ANALYSIS_MAX_WAIT_TIME,
                        "poll_interval": ANALYSIS_POLL_INTERVAL,
                    },
                )
        else:
            # Normal flow: try to fetch from database first
            try:
                if package:
                    raw_results = await repository.find_by_package(package, ecosystem, version)
                    results = self._prioritize(raw_results)
                    response = QueryResponse(
                        package=package,
                        cve_list=[CVEDetail(**item) for item in results],
                    )
                elif cve_id:
                    raw_results = await repository.find_by_cve(cve_id)
                    results = self._prioritize(raw_results)
                    response = QueryResponse(
                        cve_id=cve_id,
                        cve_list=[CVEDetail(**item) for item in results],
                    )
                else:
                    raise InvalidInputError(
                        field="package_or_cve_id",
                        reason="Either 'package' or 'cve_id' parameter must be provided",
                        details={"package": package, "cve_id": cve_id},
                    )

            except ResourceNotFound as exc:
                # Data not found - trigger analysis and wait for results
                logger.info(
                    "Data not found for %s (ecosystem=%s), triggering analysis job",
                    package or cve_id,
                    ecosystem,
                )

                # Submit analysis job to Redis
                if package:
                    success = await submit_analysis_job(
                        package_name=package,
                        version=version or "latest",
                        force=False,
                        source="web_query",
                        ecosystem=ecosystem,
                    )
                else:
                    success = await submit_analysis_job(
                        cve_id=cve_id,
                        force=False,
                        source="web_query_cve_only",
                        ecosystem=ecosystem,
                    )

                if not success:
                    logger.warning("Failed to submit analysis job for %s", package or cve_id)
                    raise

                # Poll database for results
                results = await self._poll_for_analysis_results(
                    repository, package, cve_id, version, ecosystem
                )

                if results is not None:
                    response = results
                else:
                    # Timeout - analysis still in progress
                    resource_type = "package" if package else "cve"
                    identifier = package or cve_id or "unknown"
                    raise AnalysisInProgressError(
                        resource_type=resource_type,
                        identifier=identifier,
                        details={
                            "wait_time": ANALYSIS_MAX_WAIT_TIME,
                            "poll_interval": ANALYSIS_POLL_INTERVAL,
                        },
                    )


        if redis is not None:
            try:
                await redis.set(cache_key, response.json(), ex=self._cache_ttl)
            except Exception as exc:  # pragma: no cover - cache fallback
                logger.warning("Failed to populate cache for %s", cache_key, exc_info=exc)
        return response

    @staticmethod
    def _build_cache_key(package: Optional[str], cve_id: Optional[str], version: Optional[str] = None, ecosystem: str = "npm") -> str:
        """캐시 키 생성(Create cache key).

        Args:
            package: Package name
            cve_id: CVE ID
            version: Optional version (included in cache key if provided)
            ecosystem: Package ecosystem
        """

        if package:
            if version:
                return f"query:{ecosystem}:package:{package}:v{version}"
            return f"query:{ecosystem}:package:{package}"
        if cve_id:
            return f"query:cve:{cve_id}"
        raise InvalidInputError(
            field="package_or_cve_id",
            reason="Either 'package' or 'cve_id' must be provided for cache key generation",
            details={"package": package, "cve_id": cve_id},
        )

    @staticmethod
    def _prioritize(results: List[dict[str, object]]) -> List[dict[str, object]]:
        """위협 우선순위를 계산하고 정렬(Calculate and sort threat priority)."""
        prioritized: List[dict[str, object]] = []
        for item in results:
            cvss_score = item.get("cvss_score")

            # Use risk_score from DB, default to 0.0 if missing
            risk_score = float(item.get("risk_score") or 0.0)

            # Derive risk_label based on risk_score (simple mapping)
            # P1: Score >= 8.0 (Critical/High equivalent)
            # P2: Score >= 5.0 (Medium equivalent)
            # P3: Score < 5.0 (Low equivalent)
            if risk_score >= 8.0:
                risk_label = "P1"
            elif risk_score >= 5.0:
                risk_label = "P2"
            else:
                risk_label = "P3"

            prioritized.append(
                {
                    **item,
                    "cvss_score": cvss_score,
                    "risk_score": risk_score,
                    "risk_label": risk_label,
                }
            )

        prioritized.sort(key=lambda entry: entry["risk_score"], reverse=True)
        return prioritized[:10]

    async def _poll_for_analysis_results(
        self,
        repository: QueryRepository,
        package: Optional[str],
        cve_id: Optional[str],
        version: Optional[str] = None,
        ecosystem: str = "npm",
    ) -> Optional[QueryResponse]:
        """분석 결과를 폴링으로 기다림(Poll database for analysis results).

        Args:
            repository: Query repository for database access
            package: Package name (if searching by package)
            cve_id: CVE ID (if searching by CVE)
            version: Optional package version
            ecosystem: Package ecosystem (default: "npm")

        Returns:
            QueryResponse if results found within timeout, None otherwise
        """
        elapsed = 0.0

        while elapsed < ANALYSIS_MAX_WAIT_TIME:
            try:
                # Wait before polling
                await asyncio.sleep(ANALYSIS_POLL_INTERVAL)
                elapsed += ANALYSIS_POLL_INTERVAL

                # Attempt to fetch results
                if package:
                    raw_results = await repository.find_by_package(package, ecosystem, version)
                    results = self._prioritize(raw_results)
                    response = QueryResponse(
                        package=package,
                        cve_list=[CVEDetail(**item) for item in results],
                    )
                    logger.debug(
                        "Analysis results found for package %s after %.1f seconds",
                        package,
                        elapsed,
                    )
                    return response

                elif cve_id:
                    raw_results = await repository.find_by_cve(cve_id)
                    results = self._prioritize(raw_results)
                    response = QueryResponse(
                        cve_id=cve_id,
                        cve_list=[CVEDetail(**item) for item in results],
                    )
                    logger.debug(
                        "Analysis results found for CVE %s after %.1f seconds",
                        cve_id,
                        elapsed,
                    )
                    return response

            except ResourceNotFound:
                # Results not available yet, continue polling
                logger.debug(
                    "Analysis results not yet available (elapsed: %.1f seconds)",
                    elapsed,
                )
                continue

            except Exception as exc:
                # Other errors should be logged but not stop polling
                logger.warning(
                    "Error polling for analysis results: %s (elapsed: %.1f seconds)",
                    exc,
                    elapsed,
                    exc_info=exc,
                )
                continue

        # Timeout reached
        logger.info(
            "Polling timeout reached after %.1f seconds",
            ANALYSIS_MAX_WAIT_TIME,
        )
        return None
