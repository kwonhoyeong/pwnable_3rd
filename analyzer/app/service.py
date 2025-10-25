"""Analyzer 서비스 로직(Analyzer service logic)."""
from __future__ import annotations

from datetime import datetime
from typing import List

from common_lib.ai_clients import ClaudeClient, GPT5Client
from common_lib.logger import get_logger

from .models import AnalyzerInput, AnalyzerOutput

logger = get_logger(__name__)


class RiskRuleEngine:
    """규칙 기반 위험 산정 엔진(Rule-based risk scoring engine)."""

    @staticmethod
    def classify(epss_score: float, case_count: int) -> str:
        """EPSS 및 사례 수를 바탕으로 위험 등급 산정(Classify risk level)."""

        if epss_score >= 0.7 or case_count >= 3:
            return "High"
        if epss_score >= 0.4 or case_count == 2:
            return "Medium"
        return "Low"


class RecommendationGenerator:
    """AI 기반 권고 생성기(AI-based recommendation generator)."""

    def __init__(self) -> None:
        self._client = GPT5Client()

    async def generate(self, payload: AnalyzerInput, risk_level: str) -> List[str]:
        """권고 텍스트 생성(Generate recommendation text)."""

        prompt = (
            "다음 CVE에 대해 보안 대응 권고(Security recommendations) 목록을 한국어와 영어 키워드로 작성: "
            f"CVE={payload.cve_id}, 패키지={payload.package}, 버전={payload.version_range}, "
            f"위험도(Risk level)={risk_level}. 사례 수={len(payload.cases)}"
        )
        response = await self._client.chat(prompt)
        return [line.strip() for line in response.split("\n") if line.strip()]


class SummaryGenerator:
    """분석 요약 생성기(Analysis summary generator)."""

    def __init__(self) -> None:
        self._client = ClaudeClient()

    async def generate_summary(self, payload: AnalyzerInput, risk_level: str) -> str:
        """권고 요약 텍스트 생성(Generate analysis summary)."""

        prompt = (
            "CVE {cve_id} for package {package} ({version}) has risk level {risk_level}. "
            "Summarize key attack themes and mitigation in Korean with English keywords."
        ).format(
            cve_id=payload.cve_id,
            package=payload.package,
            version=payload.version_range,
            risk_level=risk_level,
        )
        return await self._client.chat(prompt)


class AnalyzerService:
    """종합 분석 서비스(Comprehensive analysis service)."""

    def __init__(self) -> None:
        self._rules = RiskRuleEngine()
        self._recommendation = RecommendationGenerator()
        self._summary = SummaryGenerator()

    async def analyze(self, payload: AnalyzerInput) -> AnalyzerOutput:
        """위험 평가와 권고 생성 실행(Perform risk evaluation and recommendation generation)."""

        risk_level = self._rules.classify(payload.epss_score, len(payload.cases))
        recommendations = await self._recommendation.generate(payload, risk_level)
        analysis_summary = await self._summary.generate_summary(payload, risk_level)
        return AnalyzerOutput(
            cve_id=payload.cve_id,
            risk_level=risk_level,
            recommendations=recommendations,
            analysis_summary=analysis_summary,
            generated_at=datetime.utcnow(),
        )

