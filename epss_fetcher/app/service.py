"""EPSS 점수 수집 서비스 모듈(EPSS score collection service module)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

import httpx

from common_lib.logger import get_logger

logger = get_logger(__name__)


class EPSSService:
    """EPSS 점수 조회 서비스(Service fetching EPSS scores)."""

    def __init__(self, base_url: str = "https://epss.cyentia.com/api", timeout: float = 15.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def fetch_score(self, cve_id: str) -> Dict[str, Any]:
        """EPSS 점수 조회(Fetch EPSS score)."""

        retries = 3
        for attempt in range(1, retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                    response = await client.get(f"{self._base_url}/epss", params={"cve": cve_id})
                    response.raise_for_status()
                    data = response.json()
                return {
                    "cve_id": cve_id,
                    "epss_score": float(data.get("data", [{}])[0].get("epss", 0.0)),
                    "collected_at": datetime.utcnow(),
                }
            except httpx.HTTPStatusError as exc:  # pragma: no cover - skeleton fallback
                logger.warning(
                    "EPSS API HTTP 오류 발생(HTTP error on attempt %s): %s", attempt, exc
                )
                logger.debug("EPSS failure details", exc_info=exc)
            except httpx.HTTPError as exc:  # pragma: no cover - skeleton fallback
                logger.warning("EPSS API 네트워크 오류(Network error) attempt %s: %s", attempt, exc)
                logger.debug("EPSS failure details", exc_info=exc)

        logger.info(
            "EPSS API 연결 실패로 기본 점수 반환(Falling back to default EPSS score for %s)", cve_id
        )
        return {"cve_id": cve_id, "epss_score": 0.0, "collected_at": datetime.utcnow()}

