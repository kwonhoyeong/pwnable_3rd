"""EPSS 점수 수집 서비스 모듈(EPSS score collection service module)."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict

from common_lib.ai_clients import PerplexityClient
from common_lib.logger import get_logger

logger = get_logger(__name__)


class EPSSService:
    """EPSS 점수 조회 서비스(Service fetching EPSS scores)."""

    def __init__(self, timeout: float = 30.0, max_retries: int = 3) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._perplexity = PerplexityClient(timeout=timeout)

    def _validate_cve_id(self, cve_id: str) -> bool:
        """CVE ID 형식 검증(Validate CVE ID format)."""
        # CVE ID format: CVE-YYYY-NNNNN (4-digit year, 4+ digit number)
        pattern = r'^CVE-\d{4}-\d{4,}$'
        return bool(re.match(pattern, cve_id))

    async def fetch_score(self, cve_id: str) -> Dict[str, Any]:
        """EPSS 점수 조회(Fetch EPSS score using Perplexity)."""

        # Validate CVE ID to prevent prompt injection
        if not self._validate_cve_id(cve_id):
            logger.warning("Invalid CVE ID format: %s", cve_id)
            return {"cve_id": cve_id, "epss_score": 0.0, "collected_at": datetime.utcnow()}

        prompt = (
            f"Find the current EPSS (Exploit Prediction Scoring System) score for {cve_id}. "
            f"EPSS scores are probability values between 0.0 and 1.0 that estimate the likelihood "
            f"of exploitation. Please search for the most recent EPSS score and provide the exact "
            f"numeric value. Format your response as 'EPSS score: X.XXX'. If not found, respond with '0.0'."
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
                logger.warning(
                    "Perplexity API 오류(Perplexity API error for %s, attempt %s): %s",
                    cve_id,
                    attempt,
                    exc,
                )
                if attempt == self._max_retries:
                    logger.error("최대 재시도 횟수 도달(Max retries reached for %s)", cve_id)
                    return {"cve_id": cve_id, "epss_score": 0.0, "collected_at": datetime.utcnow()}
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
                    return {"cve_id": cve_id, "epss_score": 0.0, "collected_at": datetime.utcnow()}

        return {"cve_id": cve_id, "epss_score": 0.0, "collected_at": datetime.utcnow()}

    def _parse_score(self, response: str) -> float:
        """응답에서 EPSS 점수 추출(Extract EPSS score from response)."""

        # Look for patterns like "EPSS score: 0.123" or "EPSS: 0.123"
        epss_pattern = r'EPSS\s*(?:score)?:?\s*(\d*\.?\d+)'
        match = re.search(epss_pattern, response, re.IGNORECASE)

        if match:
            try:
                score = float(match.group(1))
                # EPSS scores are between 0 and 1
                if 0.0 <= score <= 1.0:
                    return score
                # Handle percentage format (e.g., 12.3% -> 0.123)
                if score > 1.0 and score <= 100.0:
                    return score / 100.0
            except ValueError:
                pass

        # Fallback: look for decimal numbers near "EPSS" keyword
        words = response.split()
        for i, word in enumerate(words):
            if 'epss' in word.lower():
                # Check next few words for a number
                for j in range(i + 1, min(i + 5, len(words))):
                    number_match = re.search(r'\d*\.?\d+', words[j])
                    if number_match:
                        try:
                            score = float(number_match.group(0))
                            if 0.0 <= score <= 1.0:
                                return score
                            if score > 1.0 and score <= 100.0:
                                return score / 100.0
                        except ValueError:
                            continue

        logger.warning("EPSS 점수를 응답에서 찾을 수 없음(Could not parse EPSS score from response): %s", response)
        return 0.0

