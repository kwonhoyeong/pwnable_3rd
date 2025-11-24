"""CVSS API 호출 서비스(Service for CVSS API calls)."""
from __future__ import annotations

import asyncio
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from common_lib.config import get_settings
from common_lib.logger import get_logger

logger = get_logger(__name__)


class CVSSService:
    """CVSS 점수 조회 서비스(Service fetching CVSS scores from NVD)."""

    NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

    def __init__(self, timeout: float = 10.0, max_retries: int = 2) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._allow_external = get_settings().allow_external_calls
        
        # NVD API 키 가져오기
        self._nvd_api_key = os.getenv("NVD_API_KEY")
        
        if not self._nvd_api_key:
            logger.warning("NVD API 키가 설정되지 않음 - 제한된 속도로 실행됩니다 (API key not set - running with rate limits)")

    @staticmethod
    def _build_response(
        cve_id: str,
        score: Optional[float] = None,
        vector: Optional[str] = None,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "cve_id": cve_id,
            "cvss_score": score,
            "vector": vector,
            "source": source,
            "collected_at": datetime.utcnow(),
        }

    def _validate_cve_id(self, cve_id: str) -> bool:
        """CVE ID 형식 검증(Validate CVE ID format)."""
        pattern = r"^CVE-\d{4}-\d{4,}$"
        return bool(re.match(pattern, cve_id))

    async def fetch_score(self, cve_id: str) -> Dict[str, Any]:
        """NVD API를 통해 CVSS 점수를 조회(Fetch CVSS score from NVD API)."""

        if not self._allow_external:
            logger.info("외부 CVSS 조회 비활성화됨(External CVSS lookups disabled); returning fallback score.")
            return self._build_response(cve_id)

        if not self._validate_cve_id(cve_id):
            logger.warning("Invalid CVE ID format: %s", cve_id)
            return self._build_response(cve_id)

        # NVD API 헤더 설정
        headers = {}
        if self._nvd_api_key:
            headers["apiKey"] = self._nvd_api_key

        params = {"cveId": cve_id}

        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.get(
                        self.NVD_API_URL,
                        headers=headers,
                        params=params,
                    )
                    
                    if response.status_code == 404:
                        logger.info("CVE not found in NVD: %s", cve_id)
                        return self._build_response(cve_id, source="not_found")
                    
                    if response.status_code == 403:
                        logger.warning("NVD API 인증 실패 - API 키 확인 필요 (Authentication failed - check API key)")
                        return self._build_response(cve_id)
                    
                    response.raise_for_status()
                    data = response.json()

                    # NVD 응답에서 CVSS 데이터 추출
                    if "vulnerabilities" in data and len(data["vulnerabilities"]) > 0:
                        vuln = data["vulnerabilities"][0]
                        cve_data = vuln.get("cve", {})
                        
                        # CVSS v3.1 또는 v3.0 우선 사용
                        metrics = cve_data.get("metrics", {})
                        cvss_score = None
                        vector = None
                        
                        # CVSS v3.1
                        if "cvssMetricV31" in metrics and len(metrics["cvssMetricV31"]) > 0:
                            cvss_data = metrics["cvssMetricV31"][0]["cvssData"]
                            cvss_score = cvss_data.get("baseScore")
                            vector = cvss_data.get("vectorString")
                        # CVSS v3.0
                        elif "cvssMetricV30" in metrics and len(metrics["cvssMetricV30"]) > 0:
                            cvss_data = metrics["cvssMetricV30"][0]["cvssData"]
                            cvss_score = cvss_data.get("baseScore")
                            vector = cvss_data.get("vectorString")
                        # CVSS v2 (fallback)
                        elif "cvssMetricV2" in metrics and len(metrics["cvssMetricV2"]) > 0:
                            cvss_data = metrics["cvssMetricV2"][0]["cvssData"]
                            cvss_score = cvss_data.get("baseScore")
                            vector = cvss_data.get("vectorString")

                        if cvss_score is not None:
                            logger.info(
                                "NVD에서 CVSS 점수 수집 성공 (Successfully fetched CVSS from NVD): %s = %.1f (attempt %d)",
                                cve_id,
                                cvss_score,
                                attempt,
                            )
                            # Rate limiting: 0.1초 대기 (Wait 0.1s to avoid rate limits)
                            await asyncio.sleep(0.1)
                            return {
                                "cve_id": cve_id,
                                "cvss_score": float(cvss_score),
                                "vector": vector,
                                "source": "NVD",
                                "collected_at": datetime.utcnow(),
                            }
                        else:
                            logger.warning("NVD 응답에 CVSS 데이터 없음 (No CVSS data in NVD response): %s", cve_id)
                            return self._build_response(cve_id, source="no_cvss_data")

                    logger.warning("NVD 응답에 취약점 데이터 없음 (No vulnerability data in NVD response): %s", cve_id)
                    return self._build_response(cve_id, source="not_found")

            except httpx.TimeoutException:
                logger.warning(
                    "NVD API 타임아웃 (NVD API timeout for %s, attempt %d)",
                    cve_id,
                    attempt,
                )
                if attempt == self._max_retries:
                    return self._build_response(cve_id)
            except httpx.HTTPError as exc:
                logger.error(
                    "NVD API HTTP 오류 (HTTP error for %s, attempt %d): %s",
                    cve_id,
                    attempt,
                    exc,
                )
                if attempt == self._max_retries:
                    return self._build_response(cve_id)
            except Exception as exc:
                logger.error(
                    "예상치 못한 오류 (Unexpected error for %s, attempt %d): %s",
                    cve_id,
                    attempt,
                    exc,
                    exc_info=True,
                )
                if attempt == self._max_retries:
                    return self._build_response(cve_id)

        return self._build_response(cve_id)
