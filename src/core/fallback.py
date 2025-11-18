"""Fallback data provider for graceful degradation when external APIs fail.

The pipeline uses fallback data when external API calls fail. This module
centralizes all fallback generation logic in one place for consistency
and ease of testing.
"""

from datetime import datetime
from typing import Any, Dict, List

from analyzer.app.models import AnalyzerInput, AnalyzerOutput
from threat_agent.app.models import ThreatCase, ThreatInput, ThreatResponse

from src.core.logger import get_logger

logger = get_logger(__name__)


class FallbackProvider:
    """Provides consistent fallback data when external APIs fail."""

    @staticmethod
    def fallback_cves(package: str) -> List[str]:
        """
        Generate fallback CVE list based on package name.

        Args:
            package: Package name (e.g., 'lodash')

        Returns:
            List with one synthetic CVE ID
        """
        suffix = abs(hash(package)) % 10000
        cve_id = f"CVE-2025-{suffix:04d}"
        logger.debug("Using fallback CVE for package=%s: %s", package, cve_id)
        return [cve_id]

    @staticmethod
    def fallback_epss(cve_id: str) -> Dict[str, Any]:
        """
        Generate fallback EPSS score.

        Args:
            cve_id: CVE identifier

        Returns:
            Dict with neutral EPSS score (0.5) and current timestamp
        """
        result = {
            "cve_id": cve_id,
            "epss_score": 0.5,  # Neutral middle value
            "collected_at": datetime.utcnow(),
        }
        logger.debug("Using fallback EPSS for %s: score=0.5", cve_id)
        return result

    @staticmethod
    def fallback_cvss(cve_id: str) -> Dict[str, Any]:
        """
        Generate fallback CVSS score.

        Args:
            cve_id: CVE identifier

        Returns:
            Dict with neutral CVSS score (5.0) and current timestamp
        """
        result = {
            "cve_id": cve_id,
            "cvss_score": 5.0,  # Neutral middle value (0-10 scale)
            "vector": None,
            "collected_at": datetime.utcnow(),
        }
        logger.debug("Using fallback CVSS for %s: score=5.0", cve_id)
        return result

    @staticmethod
    def fallback_threat_cases(payload: ThreatInput) -> ThreatResponse:
        """
        Generate fallback threat case response.

        Args:
            payload: ThreatInput with CVE, package, and version info

        Returns:
            ThreatResponse with one placeholder case
        """
        fallback_case = ThreatCase(
            source="https://example.com/prototype-case",
            title=f"Fallback case for {payload.cve_id}",
            date=datetime.utcnow().date().isoformat(),
            summary="AI API 호출 실패로 인해 기본 설명(Default narrative due to AI error).",
            collected_at=datetime.utcnow(),
        )
        result = ThreatResponse(
            cve_id=payload.cve_id,
            package=payload.package,
            version_range=payload.version_range,
            cases=[fallback_case],
        )
        logger.debug("Using fallback threat cases for %s", payload.cve_id)
        return result

    @staticmethod
    def fallback_analysis(payload: AnalyzerInput) -> AnalyzerOutput:
        """
        Generate fallback analysis result.

        Args:
            payload: AnalyzerInput with CVE, scores, and cases

        Returns:
            AnalyzerOutput with neutral risk level and canned recommendations
        """
        result = AnalyzerOutput(
            cve_id=payload.cve_id,
            risk_level="Medium",  # Neutral middle value
            recommendations=[
                "패키지를 최신 버전으로 업그레이드하세요(Upgrade package to latest).",
                "추가 모니터링을 수행하세요(Enable heightened monitoring).",
            ],
            analysis_summary="AI 분석 실패로 수동 검토 필요(Manual review required due to AI failure).",
            generated_at=datetime.utcnow(),
        )
        logger.debug("Using fallback analysis for %s", payload.cve_id)
        return result
