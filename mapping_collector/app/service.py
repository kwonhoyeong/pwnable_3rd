"""MappingCollector 비즈니스 로직(Business logic)."""
from __future__ import annotations

import asyncio
from typing import Dict, List

import httpx

from common_lib.config import get_settings
from common_lib.logger import get_logger

logger = get_logger(__name__)


class MappingService:
    """CVE 매핑 수집 서비스(Service for collecting CVE mappings)."""

    def __init__(
        self,
        cve_feed_url: str = "https://services.nvd.nist.gov/rest/json/cves/2.0",
        timeout: float = 5.0,
    ) -> None:
        self._timeout = timeout
        self._allow_external = get_settings().allow_external_calls
        self._ecosystem_endpoints: Dict[str, str] = {
            "npm": cve_feed_url,
            "pip": "https://pypi.security-data.io/api/v1/cves",
            "apt": "https://security-tracker.debian.org/tracker/api/v1/cves",
        }

    async def fetch_cves(self, package: str, version_range: str, ecosystem: str = "npm") -> List[str]:
        """외부 소스에서 CVE 목록 조회(Fetch CVE list from external source)."""

        if not self._allow_external:
            return []

        normalized_ecosystem = (ecosystem or "npm").lower()
        endpoint = self._resolve_endpoint(normalized_ecosystem)
        params = self._build_params(package, version_range, normalized_ecosystem)

        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                request = client.get(endpoint, params=params)
                response = await asyncio.wait_for(request, timeout=self._timeout)
                response.raise_for_status()
                data = response.json()
        except asyncio.TimeoutError:
            logger.info(
                "CVE feed 요청 시간 초과(Request timed out after %.1fs, ecosystem=%s); using fallback CVEs.",
                self._timeout,
                normalized_ecosystem,
            )
            return []
        except httpx.HTTPStatusError as exc:  # pragma: no cover - skeleton fallback
            logger.info(
                "CVE feed HTTP 오류 발생(HTTP error encountered, ecosystem=%s); using fallback CVEs.",
                normalized_ecosystem,
            )
            logger.debug("CVE feed failure details", exc_info=exc)
            return []
        except httpx.HTTPError as exc:  # pragma: no cover - skeleton fallback
            logger.info(
                "CVE feed 네트워크 오류(Network error, ecosystem=%s); using fallback CVEs.",
                normalized_ecosystem,
            )
            logger.debug("CVE feed failure details", exc_info=exc)
            return []

        return data.get("cve_ids", [])

    def _resolve_endpoint(self, ecosystem: str) -> str:
        return self._ecosystem_endpoints.get(ecosystem, self._ecosystem_endpoints["npm"])

    @staticmethod
    def _build_params(package: str, version_range: str, ecosystem: str) -> Dict[str, str]:
        params: Dict[str, str] = {"package": package, "ecosystem": ecosystem}
        if ecosystem == "pip":
            params["version"] = version_range
        elif ecosystem == "apt":
            params["release"] = version_range
        else:
            params["version_range"] = version_range
        return params
