"""MappingCollector 비즈니스 로직(Business logic)."""
from __future__ import annotations

from typing import List

import httpx

from common_lib.logger import get_logger

logger = get_logger(__name__)


class MappingService:
    """CVE 매핑 수집 서비스(Service for collecting CVE mappings)."""

    def __init__(self, cve_feed_url: str = "https://example.com/cve-feed", timeout: float = 30.0) -> None:
        self._cve_feed_url = cve_feed_url
        self._timeout = timeout

    async def fetch_cves(self, package: str, version_range: str) -> List[str]:
        """외부 소스에서 CVE 목록 조회(Fetch CVE list from external source)."""

        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                response = await client.get(
                    self._cve_feed_url,
                    params={"package": package, "version_range": version_range},
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - skeleton fallback
            logger.warning("CVE feed HTTP 오류 발생(HTTP error encountered): %s", exc)
            logger.debug("CVE feed failure details", exc_info=exc)
            return []
        except httpx.HTTPError as exc:  # pragma: no cover - skeleton fallback
            logger.warning("CVE feed 네트워크 오류(Network error): %s", exc)
            logger.debug("CVE feed failure details", exc_info=exc)
            return []

        return data.get("cve_ids", [])

