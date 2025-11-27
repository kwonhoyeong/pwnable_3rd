"""응답 검증기 - AI 할루시네이션 탐지 및 검증(Response validator - AI hallucination detection and validation)."""
from __future__ import annotations

import re
from typing import List, Tuple

from common_lib.logger import get_logger

from .models import AnalyzerInput

logger = get_logger(__name__)


class ResponseValidator:
    """AI 응답 검증 및 할루시네이션 탐지(AI response validation and hallucination detection)."""

    # Suspicious phrases that indicate speculation or uncertainty
    SUSPICIOUS_PHRASES = [
        "typically",
        "usually",
        "commonly",
        "often",
        "might",
        "could potentially",
        "likely",
        "probably",
        "generally",
        "in most cases",
        "tends to",
    ]

    # Positive indicators (AI acknowledging uncertainty)
    POSITIVE_INDICATORS = [
        "data not available",
        "unknown",
        "not specified",
        "not documented",
        "specific details unknown",
        "information unavailable",
    ]

    @staticmethod
    def validate_cve_report(report: str, payload: AnalyzerInput) -> Tuple[str, List[str]]:
        """
        보고서 검증 및 경고 생성(Validate report and generate warnings).

        Args:
            report: AI가 생성한 보고서
            payload: 입력 데이터

        Returns:
            (검증된 보고서, 경고 목록)
        """
        warnings = []

        # 1. CVE ID 일치 확인
        if payload.cve_id.upper() not in report.upper():
            warnings.append(f"⚠️ Report does not mention provided CVE ID: {payload.cve_id}")
            logger.warning(f"CVE ID mismatch in report for {payload.cve_id}")

        # 2. 버전 범위 일치 확인
        if payload.version_range and payload.version_range.lower() not in report.lower():
            # Allow exceptions for "all versions" or "not specified"
            if "all versions" not in report.lower() and "not specified" not in report.lower():
                warnings.append(
                    f"⚠️ Version range mismatch: expected '{payload.version_range}' but not found in report"
                )
                logger.warning(f"Version range '{payload.version_range}' not found in report")

        # 3. CVSS 점수 검증
        if payload.cvss_score is not None:
            cvss_str = f"{payload.cvss_score:.1f}"
            if cvss_str not in report:
                # Check if it mentions CVSS at all
                if "cvss" in report.lower():
                    warnings.append(
                        f"⚠️ CVSS score {cvss_str} not found in report, but CVSS is mentioned"
                    )
                else:
                    warnings.append(f"⚠️ CVSS score {cvss_str} missing from report")

        # 4. EPSS 점수 검증
        if payload.epss_score is not None:
            epss_str = f"{payload.epss_score:.3f}"
            if epss_str not in report:
                # Check if it mentions EPSS at all
                if "epss" in report.lower():
                    warnings.append(
                        f"⚠️ EPSS score {epss_str} not found in report, but EPSS is mentioned"
                    )

        # 5. 긍정적 신호 확인 (AI가 불확실성을 인정한 경우)
        uncertainty_count = sum(
            1 for phrase in ResponseValidator.POSITIVE_INDICATORS if phrase in report.lower()
        )
        if uncertainty_count > 0:
            logger.info(
                f"✅ Report acknowledges uncertainty {uncertainty_count} times - good sign of factual honesty"
            )

        # 6. 의심스러운 패턴 탐지 (추측성 언어)
        suspicious_found = []
        for phrase in ResponseValidator.SUSPICIOUS_PHRASES:
            if phrase in report.lower():
                suspicious_found.append(phrase)

        if suspicious_found:
            warnings.append(
                f"⚠️ Vague/speculative language detected: {', '.join(suspicious_found[:3])}... (may indicate hallucination)"
            )
            logger.warning(f"Suspicious phrases found in report: {suspicious_found}")

        # 7. 출처 인용 확인
        citation_patterns = [
            r"according to",
            r"based on",
            r"the cve description",
            r"threat (intelligence|data|case)",
            r"nvd reports",
        ]
        citation_count = sum(
            1 for pattern in citation_patterns if re.search(pattern, report.lower())
        )

        if citation_count == 0:
            warnings.append(
                "⚠️ No source citations found - report may lack factual grounding"
            )
            logger.warning("Report lacks source citations")
        elif citation_count >= 3:
            logger.info(f"✅ Report contains {citation_count} source citations - good factual grounding")

        # 8. 패키지 이름 확인
        if payload.package and payload.package.lower() != "generic":
            if payload.package.lower() not in report.lower():
                warnings.append(
                    f"⚠️ Package name '{payload.package}' not found in report"
                )

        # 9. 위협 사례 인용 확인 (있는 경우)
        if payload.cases and len(payload.cases) > 0:
            # Check if report mentions threat cases
            threat_mentioned = any(
                keyword in report.lower()
                for keyword in ["threat case", "exploit", "attack", "in-the-wild"]
            )
            if not threat_mentioned:
                warnings.append(
                    f"⚠️ {len(payload.cases)} threat cases provided but not mentioned in report"
                )

        # 로그 요약
        if warnings:
            logger.warning(
                f"Report validation found {len(warnings)} warnings for {payload.cve_id}"
            )
        else:
            logger.info(f"✅ Report validation passed for {payload.cve_id}")

        return report, warnings

    @staticmethod
    def calculate_hallucination_risk(warnings: List[str]) -> float:
        """
        할루시네이션 위험 점수 계산(Calculate hallucination risk score).

        Args:
            warnings: 검증 경고 목록

        Returns:
            0.0 (낮음) ~ 1.0 (높음) 사이의 위험 점수
        """
        if not warnings:
            return 0.0

        # Weight different types of warnings
        risk_score = 0.0

        for warning in warnings:
            if "CVE ID mismatch" in warning or "Package name" in warning:
                risk_score += 0.3  # Critical issue
            elif "Version range mismatch" in warning:
                risk_score += 0.2
            elif "CVSS" in warning or "EPSS" in warning:
                risk_score += 0.15
            elif "Vague/speculative language" in warning:
                risk_score += 0.1
            elif "No source citations" in warning:
                risk_score += 0.2
            elif "threat cases" in warning:
                risk_score += 0.1
            else:
                risk_score += 0.05

        # Cap at 1.0
        return min(risk_score, 1.0)
