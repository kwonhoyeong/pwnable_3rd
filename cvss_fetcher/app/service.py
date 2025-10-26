"""CVSS API 호출 서비스(Service for CVSS API calls)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

import httpx

from common_lib.logger import get_logger

logger = get_logger(__name__)


class CVSSService:
    """CVSS 점수 조회 서비스(Service fetching CVSS scores)."""

    def __init__(self, base_url: str = "https://services.nvd.nist.gov/rest/json/cve/1.0", timeout: float = 20.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def fetch_score(self, cve_id: str) -> Dict[str, Any]:
        """CVSS 점수를 조회하고 정규화(Fetch and normalize CVSS score)."""

        retries = 3
        for attempt in range(1, retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                    response = await client.get(f"{self._base_url}/{cve_id}")
                    response.raise_for_status()
                    data = response.json()
                metrics = (
                    data.get("result", {})
                    .get("CVE_Items", [{}])[0]
                    .get("impact", {})
                    .get("baseMetricV3", {})
                )
                score = float(metrics.get("cvssV3", {}).get("baseScore", 0.0))
                vector = metrics.get("cvssV3", {}).get("vectorString")
                return {
                    "cve_id": cve_id,
                    "cvss_score": score,
                    "vector": vector,
                    "collected_at": datetime.utcnow(),
                }
            except httpx.HTTPStatusError as exc:  # pragma: no cover - skeleton fallback
                logger.warning(
                    "CVSS API HTTP 오류 발생(HTTP error on attempt %s): %s", attempt, exc
                )
                logger.debug("CVSS failure details", exc_info=exc)
            except httpx.HTTPError as exc:  # pragma: no cover - skeleton fallback
                logger.warning("CVSS API 네트워크 오류(Network error) attempt %s: %s", attempt, exc)
                logger.debug("CVSS failure details", exc_info=exc)

        logger.info(
            "CVSS API 연결 실패로 기본 점수 반환(Falling back to default CVSS score for %s)", cve_id
        )
        return {"cve_id": cve_id, "cvss_score": 0.0, "vector": None, "collected_at": datetime.utcnow()}
