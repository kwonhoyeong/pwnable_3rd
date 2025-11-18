"""MappingCollector 비즈니스 로직(Business logic)."""
from __future__ import annotations

import asyncio
from typing import List

import httpx

from common_lib.config import get_settings
from common_lib.logger import get_logger

logger = get_logger(__name__)


class MappingService:
    """CVE 매핑 수집 서비스(Service for collecting CVE mappings)."""

    def __init__(self, cve_feed_url: str = "https://api.osv.dev/v1/query", timeout: float = 10.0) -> None:
        self._cve_feed_url = cve_feed_url
        self._timeout = timeout
        self._allow_external = get_settings().allow_external_calls
        self._npm_registry_url = "https://registry.npmjs.org"

    async def _resolve_version(self, package: str, version_range: str) -> str:
        """npm 레지스트리에서 실제 버전을 조회(Resolve actual version from npm registry)."""

        # If version_range is already a specific version (not "latest"), use it directly
        if version_range and version_range != "latest":
            return version_range

        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                request = client.get(f"{self._npm_registry_url}/{package}/latest")
                response = await asyncio.wait_for(request, timeout=5.0)
                response.raise_for_status()
                data = response.json()
                resolved_version = data.get("version", "latest")
                logger.debug("Resolved %s@latest to version %s", package, resolved_version)
                return resolved_version
        except Exception as exc:
            logger.warning("Failed to resolve %s version from npm registry: %s", package, exc)
            return "latest"

    async def fetch_cves(self, package: str, version_range: str) -> List[str]:
        """외부 소스에서 CVE 목록 조회(Fetch CVE list from external source using OSV API)."""

        if not self._allow_external:
            return []

        # Resolve the actual version to use
        resolved_version = await self._resolve_version(package, version_range)

        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                # OSV API requires POST request with JSON body
                payload = {
                    "package": {
                        "ecosystem": "npm",
                        "name": package,
                    },
                    "version": resolved_version,
                }
                request = client.post(
                    self._cve_feed_url,
                    json=payload,
                )
                response = await asyncio.wait_for(request, timeout=self._timeout)
                response.raise_for_status()
                data = response.json()
        except asyncio.TimeoutError:
            logger.info("OSV 호출 시간 초과(OSV request timed out after %.1fs); using fallback CVEs.", self._timeout)
            return []
        except httpx.HTTPStatusError as exc:  # pragma: no cover - skeleton fallback
            status_code = exc.response.status_code
            logger.info("OSV HTTP 오류 발생(OSV HTTP error status=%d); using fallback CVEs.", status_code)
            logger.debug("OSV failure details", exc_info=exc)
            return []
        except httpx.HTTPError as exc:  # pragma: no cover - skeleton fallback
            logger.info("OSV 네트워크 오류(OSV network error); using fallback CVEs.")
            logger.debug("OSV failure details", exc_info=exc)
            return []

        # Extract CVE IDs from OSV response
        vulnerabilities = data.get("vulns", [])
        cve_ids = [vuln.get("id") for vuln in vulnerabilities if vuln.get("id")]

        if cve_ids:
            logger.info("Fetched %d CVEs from OSV for package=%s, version=%s", len(cve_ids), package, resolved_version)

        return cve_ids
