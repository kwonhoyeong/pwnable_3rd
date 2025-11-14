"""ThreatAgent 서비스 계층 구현(ThreatAgent service layer implementations)."""
from __future__ import annotations

from datetime import datetime
import re
from typing import List
from urllib.parse import urlparse, urlunparse

from common_lib.ai_clients import ClaudeClient, PerplexityClient
from common_lib.logger import get_logger

from .models import ThreatCase, ThreatInput, ThreatResponse
from .prompts import SEARCH_PROMPT_TEMPLATE, SUMMARY_PROMPT_TEMPLATE

logger = get_logger(__name__)
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_TAG_PATTERN = re.compile(r"<[^>]+>")
_SANITIZED_FALLBACK_SOURCE = "https://example.com/sanitized-source"
_MAX_TITLE_LEN = 256
_MAX_SUMMARY_LEN = 2048


def _sanitize_text(value: str, max_length: int = _MAX_SUMMARY_LEN) -> str:
    """AI 응답 텍스트를 정규화(Sanitize AI responses for safe output)."""

    if not value:
        return ""
    cleaned = _CONTROL_CHARS.sub(" ", value)
    cleaned = _TAG_PATTERN.sub("", cleaned)
    normalized = " ".join(cleaned.split())
    return normalized[:max_length]


def _sanitize_source(value: str) -> str:
    """위협 사례 출처 URL 정화(Ensure threat case sources are safe URLs)."""

    if not value:
        return _SANITIZED_FALLBACK_SOURCE
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return _SANITIZED_FALLBACK_SOURCE
    sanitized = parsed._replace(params="", fragment="")
    return urlunparse(sanitized)


def _sanitize_case(case: ThreatCase) -> ThreatCase:
    """ThreatCase 필드 전체 정화(Sanitize every field of a ThreatCase)."""

    return case.copy(
        update={
            "source": _sanitize_source(str(case.source)),
            "title": _sanitize_text(case.title, _MAX_TITLE_LEN),
            "summary": _sanitize_text(case.summary, _MAX_SUMMARY_LEN),
        }
    )


class ThreatSearchService:
    """Perplexity 검색 서비스(Perplexity search service)."""

    def __init__(self) -> None:
        self._client = PerplexityClient()

    async def search_cases(self, payload: ThreatInput) -> List[ThreatCase]:
        """Perplexity 검색 결과에서 사례 추출(Extract cases from Perplexity results)."""

        prompt = SEARCH_PROMPT_TEMPLATE.format(
            package=payload.package,
            version_range=payload.version_range,
            cve_id=payload.cve_id,
        )
        raw_answer = await self._client.chat(prompt)
        # Skeleton: parse logic placeholder
        logger.debug("Perplexity raw answer: %s", raw_answer)
        return [
            ThreatCase(
                source=_sanitize_source("https://example.com/exploit-detail"),
                title=_sanitize_text(f"Sample case for {payload.cve_id}", _MAX_TITLE_LEN),
                date=datetime.utcnow().date().isoformat(),
                summary=_sanitize_text(raw_answer[:200]),
                collected_at=datetime.utcnow(),
            )
        ]


class ThreatSummaryService:
    """Claude 요약 서비스(Claude summarization service)."""

    def __init__(self) -> None:
        self._client = ClaudeClient()

    async def summarize(self, payload: ThreatInput, cases: List[ThreatCase]) -> str:
        """수집된 사례 요약(Summarize collected cases)."""

        references = "\n".join(f"- {case.title}: {case.source}" for case in cases)
        prompt = SUMMARY_PROMPT_TEMPLATE.format(
            cve_id=payload.cve_id,
            package=payload.package,
            version_range=payload.version_range,
            references=references,
        )
        summary = await self._client.chat(prompt)
        return _sanitize_text(summary)


class ThreatAggregationService:
    """검색 및 요약을 결합하는 서비스(Service composing search and summary)."""

    def __init__(self) -> None:
        self._search = ThreatSearchService()
        self._summary = ThreatSummaryService()

    async def collect(self, payload: ThreatInput) -> ThreatResponse:
        """검색과 요약을 실행하여 결과 반환(Execute search and summary)."""

        cases = await self._search.search_cases(payload)
        sanitized_cases = [_sanitize_case(case) for case in cases]
        if not sanitized_cases:
            logger.warning("No threat cases found for %s", payload.cve_id)
            return ThreatResponse(cve_id=payload.cve_id, package=payload.package, version_range=payload.version_range, cases=[])

        summary = await self._summary.summarize(payload, sanitized_cases)
        enriched_cases: List[ThreatCase] = []
        for case in sanitized_cases:
            merged_summary = _sanitize_text(
                f"{case.summary}\n\n요약(Summary): {summary}", _MAX_SUMMARY_LEN
            )
            enriched_cases.append(case.copy(update={"summary": merged_summary}))
        return ThreatResponse(
            cve_id=payload.cve_id,
            package=payload.package,
            version_range=payload.version_range,
            cases=enriched_cases,
        )
