"""ThreatAgent 서비스 계층 구현(ThreatAgent service layer implementations)."""
from __future__ import annotations

from datetime import datetime
import json
import re
from typing import List, Optional, Dict, Any
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


def _extract_severity(text: str) -> str:
    """텍스트에서 심각도 결정(Determine severity from text content)."""

    text_lower = text.lower()

    # Critical indicators
    if any(word in text_lower for word in ["critical", "critical vulnerability", "remote code execution", "rce", "exploit actively"]):
        return "CRITICAL"

    # High indicators
    if any(word in text_lower for word in ["exploit", "vulnerability", "breach", "attack", "compromised", "unauthorized access", "privilege escalation"]):
        return "HIGH"

    # Medium is default
    return "MEDIUM"


def _try_parse_json(text: str) -> Optional[Dict[str, Any]]:
    """JSON 파싱 시도(Attempt to parse JSON from text)."""

    try:
        # Try to find JSON object in the text
        start_idx = text.find("{")
        if start_idx == -1:
            return None

        end_idx = text.rfind("}")
        if end_idx == -1 or end_idx <= start_idx:
            return None

        json_str = text[start_idx:end_idx + 1]
        return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        return None


def _parse_threat_case(raw_answer: str, cve_id: str) -> ThreatCase:
    """AI 응답에서 위협 사례 추출(Extract threat case from AI response)."""

    title = "Threat Case"
    summary = raw_answer
    source = f"https://www.cve.org/CVERecord?id={cve_id}"

    # Try JSON parsing first
    parsed_json = _try_parse_json(raw_answer)
    if parsed_json:
        title = parsed_json.get("title") or parsed_json.get("name") or title
        summary = parsed_json.get("summary") or parsed_json.get("description") or raw_answer
        source = parsed_json.get("source") or parsed_json.get("url") or source
        logger.debug("Parsed threat case from JSON response")
    else:
        # Parse unstructured text: use first sentence as title
        sentences = [s.strip() for s in re.split(r"[.!?]+", raw_answer) if s.strip()]
        if sentences:
            title = sentences[0]
            summary = ". ".join(sentences[1:]) if len(sentences) > 1 else raw_answer
        else:
            summary = raw_answer

        # Try to extract URL from text if it looks like a source
        url_pattern = r"https?://[^\s]+"
        urls = re.findall(url_pattern, raw_answer)
        if urls:
            potential_source = urls[0]
            if _is_valid_source_url(potential_source):
                source = potential_source
                logger.debug("Extracted source URL from text: %s", source)

    # Ensure title and summary are not empty
    if not title or not title.strip():
        title = f"Threat details for {cve_id}"
    if not summary or not summary.strip():
        summary = raw_answer

    # Sanitize all fields
    sanitized_title = _sanitize_text(title, _MAX_TITLE_LEN)
    sanitized_summary = _sanitize_text(summary, _MAX_SUMMARY_LEN)
    sanitized_source = _sanitize_source(source)

    # Determine severity from summary + title
    severity = _extract_severity(f"{sanitized_title} {sanitized_summary}")

    return ThreatCase(
        source=sanitized_source,
        title=sanitized_title,
        date=datetime.utcnow().date().isoformat(),
        summary=sanitized_summary,
        collected_at=datetime.utcnow(),
    )


def _is_valid_source_url(url: str) -> bool:
    """URL이 유효한 위협 소스인지 확인(Validate if URL is a reasonable threat source)."""

    try:
        parsed = urlparse(url.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return False

        # Filter out obvious non-source URLs
        invalid_domains = ["example.com", "localhost", "127.0.0.1"]
        if any(domain in parsed.netloc for domain in invalid_domains):
            return False

        return True
    except Exception:
        return False


class ThreatSearchService:
    """Perplexity 검색 서비스(Perplexity search service)."""

    def __init__(self) -> None:
        self._client = PerplexityClient()

    async def search_cases(self, payload: ThreatInput) -> List[ThreatCase]:
        """Perplexity 검색 결과에서 사례 추출(Extract cases from Perplexity results)."""

        try:
            prompt = SEARCH_PROMPT_TEMPLATE.format(
                package=payload.package,
                version_range=payload.version_range,
                cve_id=payload.cve_id,
            )
            raw_answer = await self._client.chat(prompt)
            logger.debug("Perplexity raw answer: %s", raw_answer)

            # Parse the actual threat data from the response
            threat_case = _parse_threat_case(raw_answer, payload.cve_id)

            logger.info(
                "Extracted threat case for %s: title=%s, severity=%s",
                payload.cve_id,
                threat_case.title[:50],
                "N/A",  # Note: severity is computed but not stored in ThreatCase model
            )

            return [threat_case]
        except Exception as exc:
            logger.warning("Failed to search threat cases for %s: %s", payload.cve_id, exc)
            return []


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

        try:
            summary = await self._summary.summarize(payload, sanitized_cases)
        except Exception as exc:
            logger.warning("Failed to generate summary for %s: %s", payload.cve_id, exc)
            summary = "AI 요약 생성 실패 (원문 참고)"

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
