"""EPSS 점수 수집 서비스 모듈(EPSS score collection service module)."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Optional

from common_lib.ai_clients import PerplexityClient
from common_lib.config import get_settings
from common_lib.logger import get_logger
import re

logger = get_logger(__name__)


class EPSSService:
    """EPSS 점수 조회 서비스(Service fetching EPSS scores)."""

    def __init__(self, timeout: float = 5.0, max_retries: int = 1) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._perplexity = PerplexityClient(timeout=timeout)
        self._allow_external = get_settings().allow_external_calls

    @staticmethod
    def _build_response(cve_id: str, score: Optional[float] = None) -> Dict[str, Any]:
        return {"cve_id": cve_id, "epss_score": score, "collected_at": datetime.utcnow()}

    def _validate_cve_id(self, cve_id: str) -> bool:
        """CVE ID 형식 검증(Validate CVE ID format)."""
        # CVE ID format: CVE-YYYY-NNNNN (4-digit year, 4+ digit number)
        pattern = r'^CVE-\d{4}-\d{4,}$'
        return bool(re.match(pattern, cve_id))

    async def fetch_score(self, cve_id: str) -> Dict[str, Any]:
        """EPSS 점수 조회(Fetch EPSS score using Perplexity)."""

        if not self._allow_external:
            logger.info("외부 EPSS 조회 비활성화됨(External EPSS lookups disabled); returning fallback score.")
            return self._build_response(cve_id)

        # Validate CVE ID to prevent prompt injection
        if not self._validate_cve_id(cve_id):
            logger.warning("Invalid CVE ID format: %s", cve_id)
            return self._build_response(cve_id)

        prompt = (
            f"You are an EPSS lookup agent. Find the current EPSS (Exploit Prediction Scoring System) score "
            f"for {cve_id} from FIRST.org EPSS data. EPSS scores are probability values between 0.0 and 1.0 "
            f"that estimate the likelihood of exploitation.\n\n"
            f"Output ONLY the following JSON format. Do not output any other text.\n"
            f"{{\"epss_score\": 0.1234}}\n"
            f"If the EPSS score cannot be found, output: {{\"epss_score\": null}}"
        )

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self._perplexity.chat(prompt)
                score = self._parse_score(response)
                logger.info(
                    "EPSS 점수 수집 성공(Successfully fetched EPSS score for %s): %s (attempt %s)",
                    cve_id,
                    score,
                    attempt,
                )
                return {
                    "cve_id": cve_id,
                    "epss_score": score,
                    "collected_at": datetime.utcnow(),
                }
            except RuntimeError as exc:
                # Perplexity API errors (no API key, network issues)
                logger.info(
                    "Perplexity API 호출 불가(Unable to reach Perplexity for %s, attempt %s): %s. 폴백 사용.",
                    cve_id,
                    attempt,
                    exc,
                )
                return self._build_response(cve_id)
            except Exception as exc:
                # Unexpected errors
                logger.error(
                    "예상치 못한 오류(Unexpected error for %s, attempt %s): %s",
                    cve_id,
                    attempt,
                    exc,
                    exc_info=True,
                )
                if attempt == self._max_retries:
                    return self._build_response(cve_id)

        return self._build_response(cve_id)

    def _parse_score(self, response: str) -> Optional[float]:
        """응답에서 EPSS 점수 추출(Extract EPSS score from response using JSON parsing)."""

        try:
            # Try to parse as JSON
            data = json.loads(response.strip())
            score = data.get("epss_score", None)

            if score is None:
                return None

            # Validate score is a number and within valid range
            if isinstance(score, (int, float)):
                score_val = float(score)
                if 0.0 <= score_val <= 1.0:
                    return score_val
                # Handle percentage format (e.g., 12.3 -> 0.123)
                if score_val > 1.0 and score_val <= 100.0:
                    return score_val / 100.0
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning("Failed to parse EPSS JSON response: %s. Response: %s", e, response)

        return None
