"""QueryAPI 서비스 레이어(QueryAPI service layer)."""
from __future__ import annotations

import json
from typing import Optional

from common_lib.cache import get_redis
from common_lib.logger import get_logger

from .models import QueryResponse
from .repository import QueryRepository

logger = get_logger(__name__)


class QueryService:
    """쿼리 처리 서비스(Query handling service)."""

    def __init__(self, cache_ttl: int = 300) -> None:
        self._cache_ttl = cache_ttl

    async def query(self, repository: QueryRepository, package: Optional[str], cve_id: Optional[str]) -> QueryResponse:
        """패키지 또는 CVE 기준으로 조회(Query by package or CVE)."""

        cache_key = self._build_cache_key(package, cve_id)
        redis = await get_redis()
        cached = await redis.get(cache_key)
        if cached:
            logger.debug("Cache hit for %s", cache_key)
            return QueryResponse(**json.loads(cached))

        if package:
            results = await repository.find_by_package(package)
            response = QueryResponse(package=package, cve_list=results)
        elif cve_id:
            results = await repository.find_by_cve(cve_id)
            response = QueryResponse(cve_id=cve_id, cve_list=results)
        else:
            raise ValueError("Either package or cve_id must be provided")

        await redis.set(cache_key, response.json(), ex=self._cache_ttl)
        return response

    @staticmethod
    def _build_cache_key(package: Optional[str], cve_id: Optional[str]) -> str:
        """캐시 키 생성(Create cache key)."""

        if package:
            return f"query:package:{package}"
        if cve_id:
            return f"query:cve:{cve_id}"
        raise ValueError("Invalid cache key parameters")

