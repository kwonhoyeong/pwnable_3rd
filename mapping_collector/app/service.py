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

    def __init__(self, cve_feed_url: str = "https://api.osv.dev/v1/query", timeout: float = 5.0) -> None:
        self._cve_feed_url = cve_feed_url
        self._timeout = timeout
        self._allow_external = get_settings().allow_external_calls

    async def fetch_cves(self, package: str, version_range: str) -> List[str]:
        """외부 소스에서 CVE 목록 조회(Fetch CVE list from external source)."""

        if not self._allow_external:
            return []

        payload = {
            "package": {"name": package, "ecosystem": "npm"},
        }
        if version_range and version_range.lower() != "latest":
            payload["version"] = version_range

        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                request = client.post(self._cve_feed_url, json=payload)
                response = await asyncio.wait_for(request, timeout=self._timeout)
                response.raise_for_status()
                data = response.json()
        except asyncio.TimeoutError:
            logger.info("CVE feed 요청 시간 초과(Request timed out after %.1fs); using fallback CVEs.", self._timeout)
            return []
        except httpx.HTTPStatusError as exc:  # pragma: no cover - skeleton fallback
            logger.info("CVE feed HTTP 오류 발생(HTTP error encountered); using fallback CVEs.")
            logger.debug("CVE feed failure details", exc_info=exc)
            return []
        except httpx.HTTPError as exc:  # pragma: no cover - skeleton fallback
            logger.info("CVE feed 네트워크 오류(Network error); using fallback CVEs.")
            logger.debug("CVE feed failure details", exc_info=exc)
            return []

        vulns = data.get("vulns", [])
        cve_ids: List[str] = []
        for vuln in vulns:
            aliases = vuln.get("aliases") or []
            cve_aliases = [alias for alias in aliases if isinstance(alias, str) and alias.startswith("CVE-")]
            if cve_aliases:
                cve_ids.extend(cve_aliases)
                continue
            vuln_id = vuln.get("id")
            if isinstance(vuln_id, str) and vuln_id.startswith("CVE-"):
                cve_ids.append(vuln_id)

        # Deduplicate while preserving order
        seen = set()
        ordered: List[str] = []
        for cve in cve_ids:
            if cve in seen:
                continue
            seen.add(cve)
            ordered.append(cve)
        return ordered
