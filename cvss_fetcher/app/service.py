"""CVSS API 호출 서비스(Service for CVSS API calls)."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Optional

from common_lib.ai_clients import PerplexityClient
from common_lib.logger import get_logger

logger = get_logger(__name__)


class CVSSService:
    """CVSS 점수 조회 서비스(Service fetching CVSS scores)."""

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
        """CVSS 점수를 조회하고 정규화(Fetch and normalize CVSS score using Perplexity)."""

        # Validate CVE ID to prevent prompt injection
        if not self._validate_cve_id(cve_id):
            logger.warning("Invalid CVE ID format: %s", cve_id)
            return {"cve_id": cve_id, "cvss_score": 0.0, "vector": None, "collected_at": datetime.utcnow()}

        prompt = (
            f"Find the CVSS (Common Vulnerability Scoring System) v3 base score and vector string for {cve_id}. "
            f"CVSS v3 base scores range from 0.0 to 10.0. The vector string starts with 'CVSS:3' and contains "
            f"metrics like AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H. Please provide both values clearly labeled. "
            f"Format: 'Base Score: X.X' and 'Vector: CVSS:3.X/...'. If not found, respond with score: 0.0 and vector: None."
        )

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self._perplexity.chat(prompt)
                score, vector = self._parse_cvss_data(response)
                logger.info(
                    "CVSS 점수 수집 성공(Successfully fetched CVSS score for %s): %s (vector: %s, attempt %s)",
                    cve_id,
                    score,
                    vector,
                    attempt,
                )
                return {
                    "cve_id": cve_id,
                    "cvss_score": score,
                    "vector": vector,
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
                    return {"cve_id": cve_id, "cvss_score": 0.0, "vector": None, "collected_at": datetime.utcnow()}
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
                    return {"cve_id": cve_id, "cvss_score": 0.0, "vector": None, "collected_at": datetime.utcnow()}

        return {"cve_id": cve_id, "cvss_score": 0.0, "vector": None, "collected_at": datetime.utcnow()}

    def _parse_cvss_data(self, response: str) -> tuple[float, Optional[str]]:
        """응답에서 CVSS 점수와 벡터 문자열 추출(Extract CVSS score and vector from response)."""

        score = 0.0
        vector = None

        # Extract CVSS vector string - more permissive pattern
        # Handles variations: whitespace, trailing text, optional metrics
        vector_pattern = r'CVSS:3\.\d+/(?:[A-Z]+:[A-Z]+/?)+'
        vector_match = re.search(vector_pattern, response, re.IGNORECASE)
        if vector_match:
            # Clean up the matched vector (remove trailing slashes, extra spaces)
            vector = vector_match.group(0).strip().rstrip('/')

        # Extract numeric score - look for score in context to avoid version numbers
        # Priority 1: Look for "score: X.X" or "Base Score: X.X"
        score_pattern = r'(?:base\s+)?score[:\s]+(\d+\.?\d*)'
        score_match = re.search(score_pattern, response, re.IGNORECASE)

        if score_match:
            try:
                potential_score = float(score_match.group(1))
                if 0.0 <= potential_score <= 10.0:
                    score = potential_score
            except ValueError:
                pass

        # Priority 2: If no labeled score found, look for numbers NOT part of CVSS version
        if score == 0.0:
            # Remove the vector string from response to avoid matching its version number
            cleaned_response = re.sub(r'CVSS:3\.\d+', '', response)
            score_matches = re.findall(r'\b(\d+\.?\d*)\b', cleaned_response)
            for match in score_matches:
                try:
                    potential_score = float(match)
                    # CVSS scores are between 0.0 and 10.0 (but not 3.0, 3.1 which are versions)
                    if 0.0 <= potential_score <= 10.0 and potential_score not in [3.0, 3.1]:
                        score = potential_score
                        break
                except ValueError:
                    continue

        if score == 0.0 and vector is None:
            logger.warning("CVSS 점수를 응답에서 찾을 수 없음(Could not parse CVSS data from response): %s", response)

        return score, vector
