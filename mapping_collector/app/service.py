"""MappingCollector 비즈니스 로직(Business logic)."""
from __future__ import annotations

import asyncio
from typing import Dict, List, Optional, Tuple

import httpx

from common_lib.ai_clients import PerplexityClient
from common_lib.config import get_settings
from common_lib.logger import get_logger
from common_lib.perplexity_parsers import normalize_cve_ids, parse_cve_mapping_response

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
        self._perplexity = PerplexityClient(timeout=timeout)
        self._ecosystem_endpoints: Dict[str, str] = {
            "npm": cve_feed_url,
            "pip": "https://pypi.security-data.io/api/v1/cves",
            "apt": "https://security-tracker.debian.org/tracker/api/v1/cves",
        }

    async def fetch_cves(
        self, package: str, version_range: str, ecosystem: str = "npm"
    ) -> List[str]:
        """외부 소스에서 CVE 목록 조회(Fetch CVE list from external source)."""

        if not self._allow_external:
            return []

        normalized_ecosystem = (ecosystem or "npm").lower()
        cve_ids, source = await self._fetch_with_perplexity(package, version_range, normalized_ecosystem)
        if cve_ids:
            if source:
                logger.info("CVE fetched from Perplexity (source=%s)", source)
            return cve_ids

        cve_ids, source = await self._fetch_from_feed(package, version_range, normalized_ecosystem)
        if source:
            logger.info("CVE fetched from feed (source=%s)", source)
        return cve_ids

    def _resolve_endpoint(self, ecosystem: str) -> str:
        return self._ecosystem_endpoints.get(ecosystem, self._ecosystem_endpoints["npm"])

    @staticmethod
    def _build_params(package: str, version_range: str, ecosystem: str) -> Dict[str, str]:
        params: Dict[str, str] = {}
        if ecosystem == "pip":
            params["package"] = package
            params["version"] = version_range
            params["ecosystem"] = ecosystem # Keep for pip/apt if they use it?
        elif ecosystem == "apt":
            params["package"] = package
            params["release"] = version_range
            params["ecosystem"] = ecosystem
        else:
            # NVD 2.0 uses keywordSearch
            params["keywordSearch"] = package
        return params

    async def _fetch_with_perplexity(
        self, package: str, version_range: str, ecosystem: str
    ) -> Tuple[List[str], Optional[str]]:
        prompt = self._build_prompt(package, version_range, ecosystem)
        try:
            response = await self._perplexity.chat(prompt)
        except RuntimeError as exc:
            logger.info(
                "Perplexity 호출 실패(Perplexity unavailable for %s %s %s): %s",
                ecosystem,
                package,
                version_range,
                exc,
            )
            return [], None
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("Perplexity 호출 중 예외 발생(Unexpected error calling Perplexity)", exc_info=exc)
            return [], None

        cve_ids, source = parse_cve_mapping_response(response)
        if cve_ids:
            logger.info(
                "Perplexity 기반 CVE 조회 성공(Fetched %d CVEs via Perplexity, ecosystem=%s, source=%s)",
                len(cve_ids),
                ecosystem,
                source or "unknown",
            )
        else:
            logger.warning(
                "Perplexity 응답에 CVE 없음(No CVEs returned by Perplexity, ecosystem=%s, package=%s)",
                ecosystem,
                package,
            )
        return cve_ids, source

    async def _fetch_from_feed(
        self, package: str, version_range: str, ecosystem: str
    ) -> Tuple[List[str], Optional[str]]:
        endpoint = self._resolve_endpoint(ecosystem)
        params = self._build_params(package, version_range, ecosystem)

        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                request = client.get(endpoint, params=params)
                response = await asyncio.wait_for(request, timeout=self._timeout)
                response.raise_for_status()
                data = response.json()
        except asyncio.TimeoutError:
            logger.info(
                "CVE feed 요청 시간 초과(Request timed out after %.1fs, ecosystem=%s); returning empty list.",
                self._timeout,
                ecosystem,
            )
            return [], None
        except httpx.HTTPStatusError as exc:  # pragma: no cover - skeleton fallback
            logger.info(
                "CVE feed HTTP 오류 발생(HTTP error encountered, ecosystem=%s); returning empty list.",
                ecosystem,
            )
            logger.debug("CVE feed failure details", exc_info=exc)
            return [], None
        except httpx.HTTPError as exc:  # pragma: no cover - skeleton fallback
            logger.info(
                "CVE feed 네트워크 오류(Network error, ecosystem=%s); returning empty list.",
                ecosystem,
            )
            logger.debug("CVE feed failure details", exc_info=exc)
            return [], None
        except (ValueError, TypeError) as exc:
            logger.warning(
                "CVE feed JSON 파싱 실패(Failed to parse feed response, ecosystem=%s): %s; returning empty list.",
                ecosystem,
                exc,
            )
            logger.debug("Feed parsing failure details", exc_info=exc)
            return [], None

        # Extract CVE IDs from feed-specific schema
        cve_ids = self._extract_cves_from_feed(data, ecosystem)
        normalized = normalize_cve_ids(cve_ids)
        source = f"Feed ({ecosystem})" if normalized else None

        if normalized:
            logger.info(
                "CVE feed 기반 CVE 조회 성공(Fetched %d CVEs via feed, ecosystem=%s)",
                len(normalized),
                ecosystem,
            )
        else:
            logger.warning(
                "CVE feed 응답에 CVE 없음(No CVEs found in feed, ecosystem=%s, package=%s)",
                ecosystem,
                package,
            )

        return normalized, source

    @staticmethod
    def _extract_cves_from_feed(data: dict, ecosystem: str) -> List[str]:
        """Extract CVE IDs from feed-specific JSON schema."""

        if not isinstance(data, dict):
            return []

        # NVD schema: {"vulnerabilities": [{"cve": {"id": "CVE-YYYY-XXXX"}}, ...]}
        if ecosystem == "npm":
            vulnerabilities = data.get("vulnerabilities", [])
            if isinstance(vulnerabilities, list):
                cve_ids = []
                for vuln in vulnerabilities:
                    if isinstance(vuln, dict):
                        cve_info = vuln.get("cve", {})
                        if isinstance(cve_info, dict):
                            cve_id = cve_info.get("id")
                            if isinstance(cve_id, str):
                                cve_ids.append(cve_id)
                return cve_ids

        # PyPI schema: {"CVE_Items": [{"cve": {"ID": "CVE-YYYY-XXXX"}}, ...]}
        elif ecosystem == "pip":
            cve_items = data.get("CVE_Items", [])
            if isinstance(cve_items, list):
                cve_ids = []
                for item in cve_items:
                    if isinstance(item, dict):
                        cve_info = item.get("cve", {})
                        if isinstance(cve_info, dict):
                            cve_id = cve_info.get("ID")
                            if isinstance(cve_id, str):
                                cve_ids.append(cve_id)
                return cve_ids

        # Debian schema: {"cves": ["CVE-YYYY-XXXX", ...]}
        elif ecosystem == "apt":
            cves = data.get("cves", [])
            if isinstance(cves, list):
                return [cve for cve in cves if isinstance(cve, str)]

        # Fallback: try top-level cve_ids
        cve_ids = data.get("cve_ids", [])
        return cve_ids if isinstance(cve_ids, list) else []

    @staticmethod
    def _build_prompt(package: str, version_range: str, ecosystem: str) -> str:
        return (
            "아래 패키지와 버전 범위에 영향을 주는 CVE ID를 최신 자료 기준으로 찾아 JSON으로만 답해."
            "\n\n패키지: {package}\n버전 범위: {version_range}\n생태계: {ecosystem}\n\n"
            "출력 형식:\n"
            '{{\n  "cve_ids": ["CVE-YYYY-XXXX", ...],\n  "source": "<참조 링크 또는 not_found>"\n}}\n\n'
            "반드시 JSON만 출력하고 자연어 설명이나 코드블록은 포함하지 마."
            "찾을 수 없으면 빈 배열과 \"source\": \"not_found\" 로 응답해."
        ).format(package=package, version_range=version_range, ecosystem=ecosystem)
