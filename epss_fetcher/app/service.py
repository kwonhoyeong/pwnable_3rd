"""EPSS 점수 수집 서비스 모듈(EPSS score collection service module)."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from common_lib.config import get_settings
from common_lib.logger import get_logger

logger = get_logger(__name__)


class EPSSService:
    """EPSS 점수 조회 서비스(Service fetching EPSS scores from FIRST.org)."""

    EPSS_API_URL = "https://api.first.org/data/v1/epss"

    def __init__(self, timeout: float = 10.0, max_retries: int = 2) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._allow_external = get_settings().allow_external_calls

    @staticmethod
    def _build_response(cve_id: str, score: Optional[float] = None, source: Optional[str] = None) -> Dict[str, Any]:
        return {"cve_id": cve_id, "epss_score": score, "source": source, "collected_at": datetime.utcnow()}

    def _validate_cve_id(self, cve_id: str) -> bool:
        """CVE ID 형식 검증(Validate CVE ID format)."""
        # CVE ID format: CVE-YYYY-NNNNN (4-digit year, 4+ digit number)
        pattern = r"^CVE-\d{4}-\d{4,}$"
        return bool(re.match(pattern, cve_id))

    async def fetch_score(self, cve_id: str) -> Dict[str, Any]:
        """FIRST.org API를 통해 EPSS 점수 조회(Fetch EPSS score from FIRST.org API)."""

        if not self._allow_external:
            logger.info("외부 EPSS 조회 비활성화됨(External EPSS lookups disabled); returning fallback score.")
            return self._build_response(cve_id)

        # Validate CVE ID to prevent injection
        if not self._validate_cve_id(cve_id):
            logger.warning("Invalid CVE ID format: %s", cve_id)
            return self._build_response(cve_id)

        params = {"cve": cve_id}

        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.get(
                        self.EPSS_API_URL,
                        params=params,
                    )
                    
                    if response.status_code == 404:
                        logger.info("CVE not found in EPSS database: %s", cve_id)
                        return self._build_response(cve_id, source="not_found")
                    
                    response.raise_for_status()
                    data = response.json()

                    # FIRST.org API 응답에서 EPSS 데이터 추출
                    if "data" in data and len(data["data"]) > 0:
                        epss_data = data["data"][0]
                        epss_score = epss_data.get("epss")
                        
                        if epss_score is not None:
                            epss_score = float(epss_score)
                            logger.info(
                                "FIRST.org에서 EPSS 점수 수집 성공 (Successfully fetched EPSS from FIRST.org): %s = %.4f (attempt %d)",
                                cve_id,
                                epss_score,
                                attempt,
                            )
                            return {
                                "cve_id": cve_id,
                                "epss_score": epss_score,
                                "source": "FIRST.org",
                                "collected_at": datetime.utcnow(),
                            }
                        else:
                            logger.warning("FIRST.org 응답에 EPSS 데이터 없음 (No EPSS data in response): %s", cve_id)
                            return self._build_response(cve_id, source="no_epss_data")

                    logger.warning("FIRST.org 응답에 데이터 없음 (No data in FIRST.org response): %s", cve_id)
                    return self._build_response(cve_id, source="not_found")

            except httpx.TimeoutException:
                logger.warning(
                    "FIRST.org API 타임아웃 (FIRST.org API timeout for %s, attempt %d)",
                    cve_id,
                    attempt,
                )
                if attempt == self._max_retries:
                    return self._build_response(cve_id)
            except httpx.HTTPError as exc:
                logger.error(
                    "FIRST.org API HTTP 오류 (HTTP error for %s, attempt %d): %s",
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
                return self._build_response(cve_id)

        return self._build_response(cve_id)
