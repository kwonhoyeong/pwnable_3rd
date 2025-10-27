"""QueryAPI 서비스 레이어(QueryAPI service layer)."""
from __future__ import annotations

import json
from typing import List, Optional

from common_lib.cache import get_cache
from common_lib.logger import get_logger

from .models import CVEDetail, QueryResponse
from .repository import QueryRepository

logger = get_logger(__name__)


class QueryService:
    """쿼리 처리 서비스(Query handling service)."""

    def __init__(self, cache_ttl: int = 300) -> None:
        self._cache_ttl = cache_ttl

    async def query(self, repository: QueryRepository, package: Optional[str], cve_id: Optional[str]) -> QueryResponse:
        """패키지 또는 CVE 기준으로 조회(Query by package or CVE)."""

        cache_key = self._build_cache_key(package, cve_id)
        cache = None
        try:
            cache = await get_cache()
            cached = await cache.get(cache_key)
        except Exception as exc:  # pragma: no cover - cache fallback
            cached = None
            logger.warning("Cache unavailable, bypassing cache", exc_info=exc)
        if cached:
            logger.debug("Cache hit for %s", cache_key)
            return QueryResponse(**json.loads(cached))

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

        if cache is not None:
            try:
                await cache.set(cache_key, response.json(), ex=self._cache_ttl)
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
            "Critical": 4,
            "High": 3,
            "Medium": 2,
            "Low": 1,
            "Unknown": 0,
        }

        prioritized: List[dict[str, object]] = []
        for item in results:
            risk_level = str(item.get("risk_level", "Unknown"))
            risk_weight = risk_weights.get(risk_level, 0)
            epss_score = float(item.get("epss_score", 0.0))
            cvss_score = item.get("cvss_score")
            cvss_value = float(cvss_score) if cvss_score is not None else 0.0

            priority_score = (risk_weight * 100) + (cvss_value * 5) + (epss_score * 10)

            if risk_weight >= 3 or cvss_value >= 8.0 or epss_score >= 0.7:
                priority_label = "P1"
            elif risk_weight >= 2 or cvss_value >= 6.0 or epss_score >= 0.4:
                priority_label = "P2"
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

