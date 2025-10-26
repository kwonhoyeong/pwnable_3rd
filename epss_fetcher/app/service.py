"""EPSS API 호출 서비스(Service for EPSS API calls)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

import httpx

from common_lib.logger import get_logger

logger = get_logger(__name__)


class EPSSService:
    """EPSS 점수 조회 서비스(Service fetching EPSS scores)."""

    def __init__(self, base_url: str = "https://epss.cyentia.com/api") -> None:
        self._base_url = base_url
        self._client = httpx.AsyncClient(timeout=15.0)

    async def fetch_score(self, cve_id: str) -> Dict[str, Any]:
        """EPSS 점수 조회(Fetch EPSS score)."""

        retries = 3
        for attempt in range(1, retries + 1):
            try:
                response = await self._client.get(f"{self._base_url}/epss", params={"cve": cve_id})
                response.raise_for_status()
                data = response.json()
                return {
                    "cve_id": cve_id,
                    "epss_score": float(data.get("data", [{}])[0].get("epss", 0.0)),
                    "collected_at": datetime.utcnow(),
                }
            except httpx.HTTPError as exc:  # pragma: no cover - skeleton
                logger.warning("EPSS API attempt %s failed", attempt, exc_info=exc)
                if attempt == retries:
                    raise
        return {"cve_id": cve_id, "epss_score": 0.0, "collected_at": datetime.utcnow()}

