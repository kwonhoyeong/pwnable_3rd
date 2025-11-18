"""MappingCollector 비즈니스 로직(Business logic)."""
from __future__ import annotations

import asyncio
from typing import List, Optional

import httpx

from common_lib.config import get_settings
from common_lib.logger import get_logger
from mapping_collector.app.claude import ClaudeAnalyzer

logger = get_logger(__name__)


class MappingService:
    """CVE 매핑 수집 서비스(Service for collecting CVE mappings)."""

    def __init__(
        self,
        cve_feed_url: str = "https://api.osv.dev/v1/query",
        timeout: float = 5.0,
        use_claude_analysis: bool = True,
    ) -> None:
        self._cve_feed_url = cve_feed_url
        self._timeout = timeout
        self._allow_external = get_settings().allow_external_calls
        self._use_claude_analysis = use_claude_analysis
        self._claude_analyzer = ClaudeAnalyzer() if use_claude_analysis else None

    async def fetch_cves(self, package: str, version_range: str) -> List[str]:
        """외부 소스에서 CVE 목록 조회(Fetch CVE list from external source)."""

        if not self._allow_external:
            return []

        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                request = client.get(
                    self._cve_feed_url,
                    params={"package": package, "version_range": version_range},
                )
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

        return data.get("cve_ids", [])

    async def analyze_cves_with_claude(
        self,
        package: str,
        cve_ids: List[str],
        context: Optional[str] = None,
    ) -> Optional[str]:
        """Claude를 사용하여 CVE 데이터 분석.

        Analyze CVE data using Claude.

        Args:
            package: 패키지명 (Package name)
            cve_ids: CVE ID 목록 (List of CVE IDs)
            context: 추가 컨텍스트 (Additional context)

        Returns:
            Claude의 분석 결과 (Claude's analysis result) or None if Claude analysis is disabled
        """
        if not self._use_claude_analysis or not self._claude_analyzer:
            logger.debug("Claude analysis is disabled")
            return None

        try:
            logger.info(f"Analyzing {len(cve_ids)} CVEs for package '{package}' using Claude...")
            analysis = await self._claude_analyzer.analyze_cves(package, cve_ids, context)
            logger.info(f"Claude analysis completed for package '{package}'")
            return analysis
        except Exception as exc:
            logger.warning(f"Failed to analyze CVEs using Claude: {exc}")
            return None

    async def get_remediation_steps(
        self,
        package: str,
        version: str,
        cve_id: str,
    ) -> Optional[str]:
        """특정 CVE에 대한 완화 단계를 Claude를 통해 조회.

        Get remediation steps for a specific CVE using Claude.

        Args:
            package: 패키지명 (Package name)
            version: 현재 버전 (Current version)
            cve_id: CVE ID

        Returns:
            완화 단계 (Remediation steps) or None if Claude analysis is disabled
        """
        if not self._use_claude_analysis or not self._claude_analyzer:
            logger.debug("Claude analysis is disabled")
            return None

        try:
            logger.info(f"Getting remediation steps for {cve_id} in '{package}' v{version}...")
            steps = await self._claude_analyzer.get_remediation_steps(package, version, cve_id)
            logger.info(f"Remediation steps retrieved for {cve_id}")
            return steps
        except Exception as exc:
            logger.warning(f"Failed to get remediation steps from Claude: {exc}")
            return None
