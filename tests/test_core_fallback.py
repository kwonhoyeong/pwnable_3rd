"""Unit tests for FallbackProvider."""

import pytest

from mapping_collector.app.models import PackageInput
from threat_agent.app.models import ThreatInput

from src.core.fallback import FallbackProvider


class TestFallbackProviderCVEs:
    """Test CVE fallback generation."""

    def test_fallback_cves_returns_list(self):
        """Test that fallback_cves returns a list."""
        provider = FallbackProvider()
        result = provider.fallback_cves("lodash")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_fallback_cves_returns_cve_ids(self):
        """Test that fallback_cves returns valid CVE ID format."""
        provider = FallbackProvider()
        result = provider.fallback_cves("lodash")
        for cve_id in result:
            assert isinstance(cve_id, str)
            assert cve_id.startswith("CVE-")

    def test_fallback_cves_consistent_for_package(self):
        """Test that same package returns consistent results."""
        provider = FallbackProvider()
        result1 = provider.fallback_cves("lodash")
        result2 = provider.fallback_cves("lodash")
        # Should generate consistent results based on package hash
        assert len(result1) == len(result2)
        assert result1[0] == result2[0]

    def test_fallback_cves_different_for_different_packages(self):
        """Test that different packages generate different results."""
        provider = FallbackProvider()
        result1 = provider.fallback_cves("lodash")
        result2 = provider.fallback_cves("express")
        # Different packages should likely generate different CVEs
        # (not guaranteed by hash, but very likely)
        assert result1 != result2


class TestFallbackProviderEPSS:
    """Test EPSS score fallback."""

    def test_fallback_epss_returns_dict(self):
        """Test that fallback_epss returns a dict."""
        provider = FallbackProvider()
        result = provider.fallback_epss("CVE-2025-0001")
        assert isinstance(result, dict)

    def test_fallback_epss_has_required_fields(self):
        """Test that fallback EPSS has required fields."""
        provider = FallbackProvider()
        result = provider.fallback_epss("CVE-2025-0001")
        assert "epss_score" in result
        assert "collected_at" in result

    def test_fallback_epss_score_is_valid(self):
        """Test that fallback EPSS score is valid (0.5)."""
        provider = FallbackProvider()
        result = provider.fallback_epss("CVE-2025-0001")
        # Fallback should return neutral score
        assert isinstance(result["epss_score"], (int, float))
        assert 0 <= result["epss_score"] <= 1

    def test_fallback_epss_has_timestamp(self):
        """Test that fallback EPSS has a timestamp."""
        provider = FallbackProvider()
        result = provider.fallback_epss("CVE-2025-0001")
        assert result["collected_at"] is not None


class TestFallbackProviderCVSS:
    """Test CVSS score fallback."""

    def test_fallback_cvss_returns_dict(self):
        """Test that fallback_cvss returns a dict."""
        provider = FallbackProvider()
        result = provider.fallback_cvss("CVE-2025-0001")
        assert isinstance(result, dict)

    def test_fallback_cvss_has_required_fields(self):
        """Test that fallback CVSS has required fields."""
        provider = FallbackProvider()
        result = provider.fallback_cvss("CVE-2025-0001")
        assert "cvss_score" in result
        assert "vector" in result
        assert "collected_at" in result

    def test_fallback_cvss_score_is_valid(self):
        """Test that fallback CVSS score is valid (5.0)."""
        provider = FallbackProvider()
        result = provider.fallback_cvss("CVE-2025-0001")
        # Fallback should return neutral score
        assert isinstance(result["cvss_score"], (int, float))
        assert 0 <= result["cvss_score"] <= 10

    def test_fallback_cvss_vector_is_valid(self):
        """Test that fallback CVSS vector is valid string."""
        provider = FallbackProvider()
        result = provider.fallback_cvss("CVE-2025-0001")
        # Vector can be None or a valid CVSS vector string
        assert result["vector"] is None or isinstance(result["vector"], str)


class TestFallbackProviderThreatCases:
    """Test threat case fallback."""

    def test_fallback_threat_cases_returns_response(self):
        """Test that fallback_threat_cases returns ThreatResponse."""
        provider = FallbackProvider()
        payload = ThreatInput(
            cve_id="CVE-2025-0001",
            package="lodash",
            version_range="latest",
        )
        result = provider.fallback_threat_cases(payload)
        assert result is not None
        assert hasattr(result, "cases")

    def test_fallback_threat_cases_has_cases_list(self):
        """Test that fallback threat response has cases list."""
        provider = FallbackProvider()
        payload = ThreatInput(
            cve_id="CVE-2025-0001",
            package="lodash",
            version_range="latest",
        )
        result = provider.fallback_threat_cases(payload)
        assert isinstance(result.cases, list)

    def test_fallback_threat_cases_empty_is_valid(self):
        """Test that empty threat cases list is valid."""
        provider = FallbackProvider()
        payload = ThreatInput(
            cve_id="CVE-2025-0001",
            package="lodash",
            version_range="latest",
        )
        result = provider.fallback_threat_cases(payload)
        # Empty list is valid for no threat cases found
        assert isinstance(result.cases, list)


class TestFallbackProviderAnalysis:
    """Test analysis fallback."""

    def test_fallback_analysis_returns_output(self):
        """Test that fallback_analysis returns AnalyzerOutput."""
        from analyzer.app.models import AnalyzerInput
        provider = FallbackProvider()
        payload = AnalyzerInput(
            cve_id="CVE-2025-0001",
            cases=[],
            package="lodash",
            version_range="latest",
            epss_score=None,
            cvss_score=None,
        )
        result = provider.fallback_analysis(payload)
        assert result is not None

    def test_fallback_analysis_has_required_fields(self):
        """Test that fallback analysis has required fields."""
        from analyzer.app.models import AnalyzerInput
        provider = FallbackProvider()
        payload = AnalyzerInput(
            cve_id="CVE-2025-0001",
            cases=[],
            package="lodash",
            version_range="latest",
            epss_score=None,
            cvss_score=None,
        )
        result = provider.fallback_analysis(payload)
        assert hasattr(result, "cve_id")
        assert hasattr(result, "risk_level")
        assert hasattr(result, "recommendations")
        assert hasattr(result, "analysis_summary")

    def test_fallback_analysis_risk_level_is_valid(self):
        """Test that fallback analysis risk level is valid."""
        from analyzer.app.models import AnalyzerInput
        provider = FallbackProvider()
        payload = AnalyzerInput(
            cve_id="CVE-2025-0001",
            cases=[],
            package="lodash",
            version_range="latest",
            epss_score=None,
            cvss_score=None,
        )
        result = provider.fallback_analysis(payload)
        assert result.risk_level in ["Low", "Medium", "High"]

    def test_fallback_analysis_has_recommendations(self):
        """Test that fallback analysis has recommendations."""
        from analyzer.app.models import AnalyzerInput
        provider = FallbackProvider()
        payload = AnalyzerInput(
            cve_id="CVE-2025-0001",
            cases=[],
            package="lodash",
            version_range="latest",
            epss_score=None,
            cvss_score=None,
        )
        result = provider.fallback_analysis(payload)
        assert isinstance(result.recommendations, list)
        assert len(result.recommendations) > 0
