"""Analyzer 서비스 로직(Analyzer service logic)."""
from __future__ import annotations

import re
from datetime import datetime
from typing import List, Optional

from common_lib.ai_clients import ClaudeClient, GPT5Client, PerplexityClient
from common_lib.config import get_settings
from common_lib.logger import get_logger

from .models import AnalyzerInput, AnalyzerOutput
from .prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from .validators import ResponseValidator
from .fact_checker import NVDFactChecker
from .ensemble_validator import EnsembleValidator

logger = get_logger(__name__)


class RiskRuleEngine:
    """규칙 기반 위험 산정 엔진(Rule-based risk scoring engine)."""

    @staticmethod
    def classify(epss_score: Optional[float], cvss_score: Optional[float], case_count: int) -> str:
        """EPSS, CVSS, 사례 수를 바탕으로 위험 등급 산정(Classify risk level)."""

        epss_high = epss_score is not None and epss_score >= 0.7
        cvss_high = cvss_score is not None and cvss_score >= 8.0
        epss_medium = epss_score is not None and epss_score >= 0.4
        cvss_medium = cvss_score is not None and cvss_score >= 6.0

        if epss_high or cvss_high or case_count >= 3:
            return "High"
        if epss_medium or cvss_medium or case_count == 2:
            return "Medium"
        if epss_score is None and cvss_score is None:
            return "Unknown"
        return "Low"


class RecommendationGenerator:
    """AI 기반 권고 생성기(AI-based recommendation generator)."""

    def __init__(self) -> None:
        self._client = GPT5Client()
        self._allow_external = get_settings().allow_external_calls

    async def generate(self, payload: AnalyzerInput, risk_level: str) -> List[str]:
        """권고 텍스트 생성(Generate recommendation text)."""

        if not self._allow_external:
            logger.info("GPT-5 권고 생성 비활성화됨(GPT-5 recommendations disabled); using fallback text.")
            return self._fallback_recommendations()

        epss_display = f"{payload.epss_score:.3f}" if payload.epss_score is not None else "unknown"
        cvss_display = f"{payload.cvss_score:.1f}" if payload.cvss_score is not None else "unknown"

        prompt = (
            "다음 CVE에 대해 보안 대응 권고(Security recommendations) 목록을 한국어와 영어 키워드로 작성: "
            f"CVE={payload.cve_id}, 패키지={payload.package}, 버전={payload.version_range}, "
            f"위험도(Risk level)={risk_level}, CVSS={cvss_display}, EPSS={epss_display}. "
            f"사례 수={len(payload.cases)}"
        )
        try:
            response = await self._client.chat(prompt)
            return [line.strip() for line in response.split("\n") if line.strip()]
        except RuntimeError as exc:
            logger.info("GPT-5 권고 생성 실패, 폴백 사용(Recommendation generation falling back): %s", exc)
            return self._fallback_recommendations()

    @staticmethod
    def _fallback_recommendations() -> List[str]:
        return [
            "패키지를 최신 버전으로 업그레이드하세요 (Upgrade package to latest).",
            "보안 모니터링을 강화하세요 (Enable heightened monitoring).",
        ]


class EnterpriseAnalysisGenerator:
    """엔터프라이즈급 분석 리포트 생성기(Enterprise-grade analysis report generator)."""

    def __init__(self) -> None:
        self._client = ClaudeClient()
        self._gpt_client = GPT5Client()  # For ensemble validation
        self._perplexity = PerplexityClient()
        self._allow_external = get_settings().allow_external_calls
        self._fact_checker = NVDFactChecker()  # Phase 3: NVD cross-validation
        self._enable_ensemble = get_settings().allow_external_calls  # Ensemble requires API calls

    async def generate_analysis(self, payload: AnalyzerInput) -> tuple[str, str]:
        """AI 기반 엔터프라이즈 분석 리포트 생성(Generate enterprise analysis report)."""

        if not self._allow_external:
            logger.info("Claude 분석 비활성화됨(Claude analysis disabled); using fallback text.")
            return self._fallback_summary(), "MEDIUM"

        # Build threat context from cases
        threat_context = self._build_threat_context(payload)

        # Format display values
        cvss_display = f"{payload.cvss_score:.1f}" if payload.cvss_score is not None else "Not available"
        epss_display = f"{payload.epss_score:.3f}" if payload.epss_score is not None else "Not available"

        # Identify package if generic
        real_package = payload.package
        if payload.package.lower() == "generic":
            identified_package = await self._identify_package(payload.cve_id)
            if identified_package:
                real_package = identified_package
                threat_context += f"\n\n[Auto-Identified Context] This CVE affects package: {identified_package}"

        # Build user prompt using template
        user_prompt = USER_PROMPT_TEMPLATE.format(
            cve_id=payload.cve_id,
            package=real_package,
            version_range=payload.version_range,
            threat_context=threat_context,
            cvss_score=cvss_display,
            epss_score=epss_display,
            description=payload.description or "No description available.",
        )

        try:
            # Call Claude with system prompt to generate English report
            english_response = await self._client.chat(user_prompt, system=SYSTEM_PROMPT)

            # === Phase 3 (Optional): Multi-AI Ensemble Validation ===
            final_english_response = english_response
            ensemble_confidence = 1.0

            if self._enable_ensemble:
                try:
                    logger.info(f"Running ensemble validation (Claude + GPT-5) for {payload.cve_id}")

                    # Generate GPT-5 report in parallel
                    gpt_response = await self._gpt_client.chat(user_prompt, system=SYSTEM_PROMPT)

                    # Compare responses
                    is_consistent, discrepancies, confidence = EnsembleValidator.compare_responses(
                        english_response, gpt_response, payload.cve_id
                    )

                    ensemble_confidence = confidence

                    if is_consistent:
                        logger.info(f"✅ Ensemble validation: High consensus (confidence: {confidence:.2f})")
                    else:
                        logger.warning(
                            f"⚠️ Ensemble validation: Discrepancies found (confidence: {confidence:.2f})"
                        )

                    # Select consensus response
                    final_english_response = EnsembleValidator.select_consensus_response(
                        english_response, gpt_response, discrepancies, confidence
                    )

                except Exception as exc:
                    logger.warning(f"Ensemble validation failed for {payload.cve_id}, using Claude response: {exc}")
                    final_english_response = english_response

            # Extract AI risk level from final English response
            ai_risk_level = self._extract_ai_risk_level(final_english_response)

            # Translate to Korean
            korean_response = await self._translate_to_korean(final_english_response)

            # === Phase 2: Validate the response for hallucinations ===
            validated_response, validation_warnings = ResponseValidator.validate_cve_report(
                korean_response, payload
            )

            # Calculate hallucination risk
            hallucination_risk = ResponseValidator.calculate_hallucination_risk(validation_warnings)

            # === Phase 3: NVD cross-validation ===
            nvd_verification = None
            if self._allow_external and payload.cvss_score is not None:
                try:
                    nvd_verification = await self._fact_checker.verify_cve_details(
                        payload.cve_id, payload.cvss_score
                    )

                    if nvd_verification and not nvd_verification["verified"]:
                        for discrepancy in nvd_verification["discrepancies"]:
                            logger.warning(f"NVD cross-validation: {discrepancy}")
                            validation_warnings.append(f"🔍 NVD: {discrepancy}")
                        # Increase hallucination risk if NVD finds issues
                        hallucination_risk = min(hallucination_risk + 0.2, 1.0)
                    elif nvd_verification and nvd_verification["verified"]:
                        logger.info(f"✅ NVD cross-validation passed for {payload.cve_id}")
                except Exception as exc:
                    logger.warning(f"NVD cross-validation failed for {payload.cve_id}: {exc}")

            # Log validation results
            if validation_warnings:
                logger.warning(
                    "Report validation warnings for %s (Hallucination Risk: %.2f):",
                    payload.cve_id,
                    hallucination_risk,
                )
                for warning in validation_warnings:
                    logger.warning("  - %s", warning)
            else:
                logger.info(
                    "Report validation passed for %s (Hallucination Risk: 0.00)",
                    payload.cve_id,
                )

            logger.info(
                "Successfully generated and validated enterprise analysis for %s (AI Risk: %s, Hallucination Risk: %.2f)",
                payload.cve_id,
                ai_risk_level,
                hallucination_risk,
            )

            return validated_response, ai_risk_level
        except RuntimeError as exc:
            logger.info("Claude 분석 실패, 폴백 사용(Analysis falling back): %s", exc)
            return self._fallback_summary(), "MEDIUM"

    async def _translate_to_korean(self, english_report: str) -> str:
        """영어 보고서를 한국어로 번역(Translate English report to Korean)."""
        
        translation_prompt = f"""다음 보안 분석 보고서를 한국어로 번역해주세요.
        
**중요한 번역 규칙**:
1. 기술 용어는 반드시 영어를 괄호 안에 병기하세요.
   - 예: "원격 코드 실행(Remote Code Execution)"
   - 예: "프로토타입 오염(Prototype Pollution)"
2. 섹션 헤더는 한국어와 영어를 함께 표기하세요.
   - 예: "## 🚨 경영진 요약 (Executive Summary)"
3. 마크다운 형식은 그대로 유지하세요.
4. "AI Estimated Risk" 라인은 그대로 유지하세요.
5. 전문적이고 권위있는 어조를 유지하세요.

번역할 보고서:

{english_report}

번역된 한국어 보고서만 출력하세요. 추가 설명이나 주석은 불필요합니다."""

        try:
            # Format the prompt with the actual report
            formatted_prompt = translation_prompt.replace("{{english_report}}", english_report)
            korean_report = await self._client.chat(formatted_prompt)
            return korean_report
        except RuntimeError as exc:
            logger.warning("번역 실패, 영어 보고서 반환(Translation failed, returning English): %s", exc)
            return english_report

    async def _identify_package(self, cve_id: str) -> Optional[str]:
        """
        Identify affected package using Perplexity with validation.
        
        Enhanced with Phase 2 anti-hallucination measures:
        - Stricter prompt to request exact package name only
        - Length and format validation
        - Handling of "UNKNOWN" response
        """
        try:
            prompt = f"""What is the EXACT software package name affected by {cve_id}?

CRITICAL INSTRUCTIONS:
- Return ONLY the package name (e.g., 'lodash', 'react', 'openssl', 'nginx')
- If you're not certain, return 'UNKNOWN'
- Do not include:
  * Version numbers
  * Descriptive text or explanations
  * Multiple package names
  * Programming language names
  * Platform names

Example responses:
- Good: "lodash"
- Bad: "lodash 4.17.20"
- Bad: "The npm package lodash"
"""
            response = await self._perplexity.chat(prompt, temperature=0.1)

            # Cleanup and validation
            package_name = response.strip().split('\n')[0].strip().strip('"').strip("'")

            # === Validation checks ===
            # 1. Check for explicit "UNKNOWN"
            if package_name.upper() == 'UNKNOWN' or package_name.upper() == 'N/A':
                logger.info(f"Perplexity unable to identify package for {cve_id}")
                return None

            # 2. Length validation (package names are typically short)
            if len(package_name) > 50:
                logger.warning(
                    f"Suspicious package name from Perplexity (too long): '{package_name}' for {cve_id}"
                )
                return None

            # 3. Check for spaces (package names shouldn't have spaces)
            if ' ' in package_name:
                logger.warning(
                    f"Suspicious package name from Perplexity (contains spaces): '{package_name}' for {cve_id}"
                )
                return None

            # 4. Check for common false positives
            invalid_patterns = [
                'the package', 'software', 'library', 'framework', 'application',
                'npm package', 'python package', 'affects', 'vulnerability', 'cve'
            ]
            if any(pattern in package_name.lower() for pattern in invalid_patterns):
                logger.warning(
                    f"Suspicious package name from Perplexity (descriptive text detected): '{package_name}' for {cve_id}"
                )
                return None

            # 5. Empty or very short check
            if len(package_name) < 2:
                logger.warning(f"Package name too short: '{package_name}' for {cve_id}")
                return None

            logger.info(f"✅ Successfully identified package for {cve_id}: {package_name}")
            return package_name

        except Exception as exc:
            logger.warning(f"Failed to identify package for {cve_id}: {exc}")
            return None

    @staticmethod
    def _build_threat_context(payload: AnalyzerInput) -> str:
        """위협 사례에서 컨텍스트 구성(Build threat context from cases)."""
        if not payload.cases:
            return "No specific threat cases documented."

        case_summaries = []
        for i, case in enumerate(payload.cases[:3], 1):  # Limit to 3 cases
            title = case.get("title", "Case")
            summary = case.get("summary", "")[:200]  # First 200 chars
            case_summaries.append(f"{i}. {title}: {summary}")

        return "\n".join(case_summaries)

    @staticmethod
    def _extract_ai_risk_level(response: str) -> str:
        """응답에서 AI 위험 등급 추출(Extract AI risk level from response)."""
        # Look for "AI Estimated Risk: [LEVEL]" pattern
        pattern = r"AI\s+Estimated\s+Risk\s*:\s*(CRITICAL|HIGH|MEDIUM|LOW)"
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            return match.group(1).upper()

        # Fallback: search for risk keywords in the response
        response_lower = response.lower()
        if any(word in response_lower for word in ["critical", "severe", "exploitation"]):
            return "CRITICAL"
        if any(word in response_lower for word in ["high", "significant"]):
            return "HIGH"
        if any(word in response_lower for word in ["medium", "moderate"]):
            return "MEDIUM"

        return "MEDIUM"  # Default fallback

    @staticmethod
    def _fallback_summary() -> str:
        return """## 🚨 경영진 요약 (Executive Summary)
AI 분석을 생성할 수 없습니다. 수동 검토가 필요합니다. (Unable to generate AI analysis. Manual review required.)

## 📊 취약점 스코어카드 (Vulnerability Scorecard)
자동 분석을 위한 데이터가 부족합니다. (Insufficient data for automated analysis.)

## ⚔️ 공격 시나리오 (Attack Scenario)
자동 분석을 위한 데이터가 부족합니다. (Insufficient data for automated analysis.)

## 🛡️ CIA 영향 분석 (CIA Impact Analysis)
자동 분석을 위한 데이터가 부족합니다. (Insufficient data for automated analysis.)

## 🛠️ 기술적 심층 분석 (Technical Deep Dive)
자동 분석을 위한 데이터가 부족합니다. (Insufficient data for automated analysis.)

## ✅ 대응 및 완화 전략 (Remediation Strategy)
보안 권고 및 패키지 문서를 참조하세요. (See security advisories and package documentation.)

## ⚖️ AI Estimated Risk
MEDIUM

---
*참고: 이 보고서는 AI 서비스 사용 불가로 인한 대체 보고서입니다. (Note: This is a fallback report due to AI service unavailability.)*"""


class WeightedScoringEngine:
    """가중치 기반 위험 점수 계산 엔진(Weighted risk scoring engine)."""

    # AI Risk level to numeric score mapping
    AI_RISK_SCORE_MAP = {
        "CRITICAL": 9.5,
        "HIGH": 7.5,
        "MEDIUM": 5.0,
        "LOW": 2.0,
    }

    @staticmethod
    def calculate_weighted_score(
        cvss_score: Optional[float],
        epss_score: Optional[float],
        ai_risk_level: str,
    ) -> float:
        """
        가중치 기반 위험 점수 계산.
        Formula: score = (cvss_val * 0.4) + (epss_val * 10 * 0.3) + (ai_score * 0.3)

        Calculate weighted risk score.
        CVSS (0-10) * 0.4 + EPSS (0-1, scaled to 0-10) * 0.3 + AI Score * 0.3
        """

        # Normalize values (treat None as 0.0)
        cvss_val = cvss_score if cvss_score is not None else 0.0
        epss_val = epss_score if epss_score is not None else 0.0

        # Scale EPSS from 0-1 to 0-10
        epss_scaled = epss_val * 10

        # Get AI score from mapping
        ai_score = WeightedScoringEngine.AI_RISK_SCORE_MAP.get(ai_risk_level.upper(), 5.0)

        # Calculate weighted score
        weighted_score = (cvss_val * 0.4) + (epss_scaled * 0.3) + (ai_score * 0.3)

        # Ensure the result is within 0-10 range
        return min(10.0, max(0.0, weighted_score))

    @staticmethod
    def score_to_risk_level(score: float) -> str:
        """점수를 위험 등급으로 변환(Convert numeric score to risk level)."""
        if score >= 8.0:
            return "CRITICAL"
        if score >= 6.0:
            return "HIGH"
        if score >= 4.0:
            return "MEDIUM"
        return "LOW"


class AnalyzerService:
    """종합 분석 서비스(Comprehensive analysis service)."""

    def __init__(self) -> None:
        self._rules = RiskRuleEngine()
        self._recommendation = RecommendationGenerator()
        self._analysis = EnterpriseAnalysisGenerator()
        self._scoring = WeightedScoringEngine()

    async def analyze(self, payload: AnalyzerInput) -> AnalyzerOutput:
        """위험 평가와 권고 생성 실행(Perform risk evaluation and recommendation generation)."""

        # Generate enterprise analysis and extract AI risk level
        analysis_summary, ai_risk_level = await self._analysis.generate_analysis(payload)

        # Calculate weighted risk score
        risk_score = self._scoring.calculate_weighted_score(
            payload.cvss_score,
            payload.epss_score,
            ai_risk_level,
        )

        # Determine risk level based on the calculated weighted score
        risk_level = self._scoring.score_to_risk_level(risk_score)

        # Generate recommendations
        recommendations = await self._recommendation.generate(payload, risk_level)

        logger.info(
            "Analysis completed for %s: risk_level=%s, score=%.2f",
            payload.cve_id,
            risk_level,
            risk_score,
        )

        return AnalyzerOutput(
            cve_id=payload.cve_id,
            risk_level=risk_level,
            risk_score=risk_score,
            recommendations=recommendations,
            analysis_summary=analysis_summary,
            generated_at=datetime.utcnow(),
        )
