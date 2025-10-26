"""ThreatAgent 서비스 계층 구현(ThreatAgent service layer implementations)."""
from __future__ import annotations

from datetime import datetime
from typing import List

from common_lib.ai_clients import ClaudeClient, PerplexityClient
from common_lib.logger import get_logger

from .models import ThreatCase, ThreatInput, ThreatResponse
from .prompts import SEARCH_PROMPT_TEMPLATE, SUMMARY_PROMPT_TEMPLATE

logger = get_logger(__name__)


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
                source="https://example.com/exploit-detail",
                title=f"Sample case for {payload.cve_id}",
                date=datetime.utcnow().date().isoformat(),
                summary=raw_answer[:200],
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
        return summary


class ThreatAggregationService:
    """검색 및 요약을 결합하는 서비스(Service composing search and summary)."""

    def __init__(self) -> None:
        self._search = ThreatSearchService()
        self._summary = ThreatSummaryService()

    async def collect(self, payload: ThreatInput) -> ThreatResponse:
        """검색과 요약을 실행하여 결과 반환(Execute search and summary)."""

        cases = await self._search.search_cases(payload)
        if not cases:
            logger.warning("No threat cases found for %s", payload.cve_id)
            return ThreatResponse(cve_id=payload.cve_id, package=payload.package, version_range=payload.version_range, cases=[])

        summary = await self._summary.summarize(payload, cases)
        enriched_cases = [
            case.copy(update={"summary": f"{case.summary}\n\n요약(Summary): {summary}"}) for case in cases
        ]
        return ThreatResponse(
            cve_id=payload.cve_id,
            package=payload.package,
            version_range=payload.version_range,
            cases=enriched_cases,
        )

