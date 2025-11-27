"""NVD API 사실 검증기 - AI 주장을 공식 데이터와 교차 검증(NVD API fact-checker - Cross-validate AI claims with official data)."""
from __future__ import annotations

import asyncio
from typing import Dict, List, Optional, Tuple

import httpx

from common_lib.logger import get_logger

logger = get_logger(__name__)


class NVDFactChecker:
    """NVD API를 사용하여 AI 주장 검증(Verify AI claims using NVD API)."""

    NVD_API_BASE = "https://services.nvd.nist.gov/rest/json/cves/2.0"
    REQUEST_TIMEOUT = 10.0

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize NVD fact checker.

        Args:
            api_key: Optional NVD API key for higher rate limits
        """
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=self.REQUEST_TIMEOUT)

    async def verify_cve_details(
        self, cve_id: str, ai_cvss_score: Optional[float] = None
    ) -> Dict[str, any]:
        """
        NVD에서 CVE 세부사항 가져와서 AI 주장과 비교(Fetch CVE details from NVD and compare with AI claims).

        Args:
            cve_id: CVE 식별자
            ai_cvss_score: AI가 보고한 CVSS 점수

        Returns:
            {
                'verified': bool,
                'nvd_data': {...},
                'discrepancies': [...]
            }
        """
        try:
            # Fetch from NVD
            nvd_data = await self._fetch_cve_from_nvd(cve_id)

            if not nvd_data:
                return {
                    "verified": False,
                    "nvd_data": None,
                    "discrepancies": ["NVD data not available"],
                }

            # Extract NVD information
            nvd_cvss = self._extract_cvss_from_nvd(nvd_data)
            nvd_description = self._extract_description_from_nvd(nvd_data)

            discrepancies = []

            # Verify CVSS score
            if ai_cvss_score is not None and nvd_cvss is not None:
                # Allow 0.5 tolerance for CVSS score differences
                if abs(ai_cvss_score - nvd_cvss) > 0.5:
                    discrepancies.append(
                        f"CVSS mismatch: AI reported {ai_cvss_score:.1f}, NVD has {nvd_cvss:.1f}"
                    )
                    logger.warning(
                        f"CVSS discrepancy for {cve_id}: AI={ai_cvss_score:.1f}, NVD={nvd_cvss:.1f}"
                    )
                else:
                    logger.info(f"✅ CVSS score verified for {cve_id}")

            return {
                "verified": len(discrepancies) == 0,
                "nvd_data": {
                    "cvss_score": nvd_cvss,
                    "description": nvd_description,
                    "cve_id": cve_id,
                },
                "discrepancies": discrepancies,
            }

        except Exception as exc:
            logger.error(f"Failed to verify CVE details for {cve_id}: {exc}")
            return {
                "verified": False,
                "nvd_data": None,
                "discrepancies": [f"NVD verification failed: {exc}"],
            }

    async def _fetch_cve_from_nvd(self, cve_id: str) -> Optional[Dict]:
        """NVD API에서 CVE 데이터 가져오기(Fetch CVE data from NVD API)."""
        try:
            headers = {}
            if self._api_key:
                headers["apiKey"] = self._api_key

            params = {"cveId": cve_id}

            response = await self._client.get(
                self.NVD_API_BASE, params=params, headers=headers
            )

            if response.status_code == 429:
                logger.warning(f"NVD API rate limit hit for {cve_id}")
                # Wait and retry once
                await asyncio.sleep(6)
                response = await self._client.get(
                    self.NVD_API_BASE, params=params, headers=headers
                )

            if response.status_code == 200:
                data = response.json()
                vulnerabilities = data.get("vulnerabilities", [])
                if vulnerabilities:
                    return vulnerabilities[0].get("cve", {})
                else:
                    logger.warning(f"No vulnerabilities found in NVD for {cve_id}")
                    return None
            else:
                logger.warning(
                    f"NVD API returned status {response.status_code} for {cve_id}"
                )
                return None

        except Exception as exc:
            logger.error(f"Error fetching from NVD for {cve_id}: {exc}")
            return None

    @staticmethod
    def _extract_cvss_from_nvd(nvd_data: Dict) -> Optional[float]:
        """NVD 데이터에서 CVSS 점수 추출(Extract CVSS score from NVD data)."""
        try:
            metrics = nvd_data.get("metrics", {})

            # Try CVSS v3.1 first
            if "cvssMetricV31" in metrics:
                cvss_data = metrics["cvssMetricV31"]
                if cvss_data:
                    return cvss_data[0]["cvssData"].get("baseScore")

            # Fallback to CVSS v3.0
            if "cvssMetricV30" in metrics:
                cvss_data = metrics["cvssMetricV30"]
                if cvss_data:
                    return cvss_data[0]["cvssData"].get("baseScore")

            # Fallback to CVSS v2
            if "cvssMetricV2" in metrics:
                cvss_data = metrics["cvssMetricV2"]
                if cvss_data:
                    return cvss_data[0]["cvssData"].get("baseScore")

            return None

        except (KeyError, IndexError, TypeError) as exc:
            logger.warning(f"Failed to extract CVSS from NVD data: {exc}")
            return None

    @staticmethod
    def _extract_description_from_nvd(nvd_data: Dict) -> Optional[str]:
        """NVD 데이터에서 설명 추출(Extract description from NVD data)."""
        try:
            descriptions = nvd_data.get("descriptions", [])
            for desc in descriptions:
                if desc.get("lang") == "en":
                    return desc.get("value")
            return None
        except (KeyError, TypeError) as exc:
            logger.warning(f"Failed to extract description from NVD data: {exc}")
            return None

    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()
