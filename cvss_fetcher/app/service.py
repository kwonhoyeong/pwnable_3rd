"""CVSS API 호출 서비스(Service for CVSS API calls)."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Optional

from common_lib.ai_clients import PerplexityClient
from common_lib.config import get_settings
from common_lib.logger import get_logger
from common_lib.perplexity_parsers import parse_cvss_response

logger = get_logger(__name__)


class CVSSService:
    """CVSS 점수 조회 서비스(Service fetching CVSS scores)."""

    def __init__(self, timeout: float = 5.0, max_retries: int = 1) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._perplexity = PerplexityClient(timeout=timeout)
        self._allow_external = get_settings().allow_external_calls

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
        """CVSS 점수를 조회하고 정규화(Fetch and normalize CVSS score using Perplexity)."""

        if not self._allow_external:
            logger.info("외부 CVSS 조회 비활성화됨(External CVSS lookups disabled); returning fallback score.")
            return self._build_response(cve_id)

        if not self._validate_cve_id(cve_id):
            logger.warning("Invalid CVE ID format: %s", cve_id)
            return self._build_response(cve_id)

        prompt = (
            "다음 CVE의 CVSS 점수와 벡터를 알려줘.\n\n"
            f"CVE ID: {cve_id}\n\n"
            "반드시 아래 JSON 형식만 출력해. 설명, 자연어, 코드블록, 주석 등은 절대 포함하지 마.\n\n"
            '{\n  "cvss_score": <0과 10 사이의 숫자 또는 null>,\n'
            '  "vector": "<CVSS 벡터 문자열 또는 null>",\n'
            '  "source": "<CVSS 정보를 참고한 URL 또는 \'not_found\'>"\n}\n\n'
            '찾을 수 없으면 "cvss_score": null, "vector": null, "source": "not_found"로 답해.'
        )

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self._perplexity.chat(prompt)
                score, vector, source = parse_cvss_response(response)
                if score is not None or vector:
                    logger.info(
                        "CVSS 점수 수집 성공(Successfully fetched CVSS score for %s): %s (vector: %s, attempt %s)",
                        cve_id,
                        score,
                        vector,
                        attempt,
                    )
                else:
                    logger.warning(
                        "CVSS 점수를 응답에서 찾을 수 없음(Could not parse CVSS data from response): %s",
                        (response or "")[:300],
                    )
                return {
                    "cve_id": cve_id,
                    "cvss_score": score,
                    "vector": vector,
                    "source": source,
                    "collected_at": datetime.utcnow(),
                }
            except RuntimeError as exc:
                logger.info(
                    "Perplexity API 호출 불가(Unable to reach Perplexity for %s, attempt %s): %s. 폴백 사용.",
                    cve_id,
                    attempt,
                    exc,
                )
                return self._build_response(cve_id)
            except Exception as exc:
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
