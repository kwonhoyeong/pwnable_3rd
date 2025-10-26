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
        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
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
            except httpx.HTTPError as exc:  # pragma: no cover - skeleton fallback
                last_error = exc
                logger.warning("CVSS API attempt %s failed", attempt, exc_info=exc)
        if last_error:
            raise last_error
        return {"cve_id": cve_id, "cvss_score": 0.0, "vector": None, "collected_at": datetime.utcnow()}
