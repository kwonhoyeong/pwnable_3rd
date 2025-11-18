"""CVSS API 호출 서비스(Service for CVSS API calls)."""
from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, Optional

from common_lib.ai_clients import PerplexityClient
from common_lib.config import get_settings
from common_lib.logger import get_logger

logger = get_logger(__name__)


class CVSSService:
    """CVSS 점수 조회 서비스(Service fetching CVSS scores)."""

    def __init__(self, timeout: float = 5.0, max_retries: int = 1) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._perplexity = PerplexityClient(timeout=timeout)
        self._allow_external = get_settings().allow_external_calls

    @staticmethod
    def _build_response(cve_id: str, score: Optional[float] = None, vector: Optional[str] = None) -> Dict[str, Any]:
        return {
            "cve_id": cve_id,
            "cvss_score": score,
            "vector": vector,
            "collected_at": datetime.utcnow(),
        }

    def _validate_cve_id(self, cve_id: str) -> bool:
        """CVE ID 형식 검증(Validate CVE ID format)."""
        # CVE ID format: CVE-YYYY-NNNNN (4-digit year, 4+ digit number)
        pattern = r'^CVE-\d{4}-\d{4,}$'
        return bool(re.match(pattern, cve_id))

    async def fetch_score(self, cve_id: str) -> Dict[str, Any]:
        """CVSS 점수를 조회하고 정규화(Fetch and normalize CVSS score using Perplexity)."""

        if not self._allow_external:
            logger.info("외부 CVSS 조회 비활성화됨(External CVSS lookups disabled); returning fallback score.")
            return self._build_response(cve_id)

        # Validate CVE ID to prevent prompt injection
        if not self._validate_cve_id(cve_id):
            logger.warning("Invalid CVE ID format: %s", cve_id)
            return self._build_response(cve_id)

        prompt = (
            f"You are a CVSS lookup agent. Find the latest CVSS v3 base score and vector string for {cve_id} "
            f"from official NVD or CVE databases. CVSS v3 base scores range from 0.0 to 10.0. "
            f"The vector string starts with 'CVSS:3' and contains metrics like AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H.\n\n"
            f"Output ONLY the following JSON format. Do not output any other text.\n"
            f'{{\"cvss_score\": 7.5, \"vector\": \"CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H\"}}\n'
            f'If the CVSS information cannot be found, output: {{\"cvss_score\": null, \"vector\": null}}'
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

    def _parse_cvss_data(self, response: str) -> tuple[Optional[float], Optional[str]]:
        """응답에서 CVSS 점수와 벡터 문자열 추출(Extract CVSS score and vector from response using JSON parsing)."""

        try:
            # Try to parse as JSON
            data = json.loads(response.strip())
            score = data.get("cvss_score", None)
            vector = data.get("vector", None)

            # Validate score
            if isinstance(score, (int, float)):
                score_val = float(score)
                if 0.0 <= score_val <= 10.0:
                    score = score_val
                else:
                    score = None
            elif score is not None:
                # Score is not a valid number
                score = None

            # Validate vector
            if vector is not None and not isinstance(vector, str):
                vector = None
            elif isinstance(vector, str) and vector.strip():
                vector = vector.strip()
            else:
                vector = None

            return score, vector
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning("Failed to parse CVSS JSON response: %s. Response: %s", e, response)
            return None, None
