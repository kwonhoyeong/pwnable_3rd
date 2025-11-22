"""QueryAPI 서비스 레이어(QueryAPI service layer)."""
from __future__ import annotations

import asyncio
import json
from typing import List, Optional

from common_lib.cache import get_redis
from common_lib.errors import AnalysisInProgressError, ResourceNotFound
from common_lib.logger import get_logger

from .models import CVEDetail, QueryResponse
from .repository import QueryRepository
from .redis_ops import submit_analysis_job

logger = get_logger(__name__)

# Analysis trigger and wait configuration
ANALYSIS_POLL_INTERVAL = 2.0  # seconds between polls
ANALYSIS_MAX_WAIT_TIME = 30.0  # total seconds to wait for results


class QueryService:
    """쿼리 처리 서비스(Query handling service)."""

    def __init__(self, cache_ttl: int = 300) -> None:
        self._cache_ttl = cache_ttl

    async def query(self, repository: QueryRepository, package: Optional[str], cve_id: Optional[str]) -> QueryResponse:
        """패키지 또는 CVE 기준으로 조회(Query by package or CVE).

        If data is not found, triggers analysis and polls for results.
        """

        cache_key = self._build_cache_key(package, cve_id)
        redis = None
        try:
            redis = await get_redis()
            cached = await redis.get(cache_key)
        except Exception as exc:  # pragma: no cover - cache fallback
            cached = None
            logger.warning("Redis unavailable, bypassing cache", exc_info=exc)
        if cached:
            logger.debug("Cache hit for %s", cache_key)
            return QueryResponse(**json.loads(cached))

        try:
            if package:
                raw_results = await repository.find_by_package(package)
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
                raise ValueError("Either package or cve_id must be provided")

        except ResourceNotFound as exc:
            # Data not found - trigger analysis and wait for results
            logger.info(
                "Data not found for %s, triggering analysis job",
                package or cve_id,
            )

            # Submit analysis job to Redis
            success = await submit_analysis_job(
                package_name=package or cve_id or "unknown",
                version=None,  # Use default "latest"
                force=False,
                source="web_query",
            )

            if not success:
                logger.warning(
                    "Failed to submit analysis job for %s, re-raising original error",
                    package or cve_id,
                )
                raise

            # Poll database for results
            logger.info(
                "Polling database for analysis results for %s",
                package or cve_id,
            )
            results = await self._poll_for_analysis_results(
                repository, package, cve_id
            )

            if results is not None:
                # Found results after analysis
                logger.info(
                    "Analysis results found for %s after polling",
                    package or cve_id,
                )
                response = results
            else:
                # Timeout - analysis still in progress
                logger.info(
                    "Analysis still in progress for %s after %.1f seconds",
                    package or cve_id,
                    ANALYSIS_MAX_WAIT_TIME,
                )
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
    def _build_cache_key(package: Optional[str], cve_id: Optional[str]) -> str:
        """캐시 키 생성(Create cache key)."""

        if package:
            return f"query:package:{package}"
        if cve_id:
            return f"query:cve:{cve_id}"
        raise ValueError("Invalid cache key parameters")

    @staticmethod
    def _prioritize(results: List[dict[str, object]]) -> List[dict[str, object]]:
        """위협 우선순위를 계산하고 정렬(Calculate and sort threat priority)."""

        risk_weights = {
            "CRITICAL": 4,
            "HIGH": 3,
            "MEDIUM": 2,
            "LOW": 1,
            "UNKNOWN": 0,
        }

        prioritized: List[dict[str, object]] = []
        for item in results:
            risk_level = str(item.get("risk_level", "Unknown"))
            normalized_level = risk_level.upper()
            risk_weight = risk_weights.get(normalized_level, risk_weights["UNKNOWN"])
            epss_value = item.get("epss_score")
            epss_score = float(epss_value) if epss_value is not None else None
            cvss_score = item.get("cvss_score")
            cvss_value = float(cvss_score) if cvss_score is not None else None

            priority_score = risk_weight * 100
            if cvss_value is not None:
                priority_score += cvss_value * 5
            if epss_score is not None:
                priority_score += epss_score * 10

            if risk_weight >= 3 or (cvss_value is not None and cvss_value >= 8.0) or (
                epss_score is not None and epss_score >= 0.7
            ):
                priority_label = "P1"
            elif risk_weight >= 2 or (cvss_value is not None and cvss_value >= 6.0) or (
                epss_score is not None and epss_score >= 0.4
            ):
                priority_label = "P2"
            elif epss_score is None and cvss_value is None:
                priority_label = "P2" if risk_weight else "P3"
            else:
                priority_label = "P3"

            prioritized.append(
                {
                    **item,
                    "cvss_score": cvss_score,
                    "priority_score": priority_score,
                    "priority_label": priority_label,
                }
            )

        prioritized.sort(key=lambda entry: entry["priority_score"], reverse=True)
        return prioritized

    async def _poll_for_analysis_results(
        self,
        repository: QueryRepository,
        package: Optional[str],
        cve_id: Optional[str],
    ) -> Optional[QueryResponse]:
        """분석 결과를 폴링으로 기다림(Poll database for analysis results).

        Args:
            repository: Query repository for database access
            package: Package name (if searching by package)
            cve_id: CVE ID (if searching by CVE)

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
                    raw_results = await repository.find_by_package(package)
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
