"""EPSS 점수 수집 서비스 모듈(EPSS score collection service module)."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Optional

from common_lib.ai_clients import PerplexityClient
from common_lib.config import get_settings
from common_lib.logger import get_logger
from common_lib.perplexity_parsers import parse_epss_response

logger = get_logger(__name__)


class EPSSService:
    """EPSS 점수 조회 서비스(Service fetching EPSS scores)."""

    def __init__(self, timeout: float = 5.0, max_retries: int = 1) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._perplexity = PerplexityClient(timeout=timeout)
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
        """EPSS 점수 조회(Fetch EPSS score using Perplexity)."""

        if not self._allow_external:
            logger.info("외부 EPSS 조회 비활성화됨(External EPSS lookups disabled); returning fallback score.")
            return self._build_response(cve_id)

        # Validate CVE ID to prevent prompt injection
        if not self._validate_cve_id(cve_id):
            logger.warning("Invalid CVE ID format: %s", cve_id)
            return self._build_response(cve_id)

        prompt = (
            "다음 CVE의 EPSS 점수를 알려줘.\n\n"
            f"CVE ID: {cve_id}\n\n"
            "반드시 아래 JSON 형식만 출력해. 설명, 자연어, 코드블록, 주석 등은 절대 포함하지 마.\n\n"
            '{\n  "epss_score": <0과 1 사이의 숫자 또는 null>,\n'
            '  "source": "<EPSS 정보를 참고한 URL 또는 \'not_found\'>" \n}\n\n'
            '찾을 수 없으면 "epss_score": null, "source": "not_found"로 답해.'
        )

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self._perplexity.chat(prompt)
                score, source = parse_epss_response(response)
                if score is not None:
                    logger.info(
                        "EPSS 점수 수집 성공(Successfully fetched EPSS score for %s): %s (attempt %s)",
                        cve_id,
                        score,
                        attempt,
                    )
                else:
                    logger.warning(
                        "EPSS 점수를 응답에서 찾을 수 없음(Could not parse EPSS score from response): %s",
                        (response or "")[:300],
                    )

                return {
                    "cve_id": cve_id,
                    "epss_score": score,
                    "source": source,
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
