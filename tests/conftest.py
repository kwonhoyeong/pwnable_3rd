"""Pytest configuration and shared fixtures."""
import asyncio
import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_orchestrator import AgentOrchestrator
from common_lib.cache import AsyncCache
from common_lib.logger import get_logger

logger = get_logger(__name__)


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest.fixture
async def mock_cache():
    """Create a mock cache for testing."""
    cache = AsyncCache(namespace="test")
    yield cache
    # Cleanup
    await cache.clear_namespace()


@pytest.fixture
def sample_package():
    """Sample package name for testing."""
    return "lodash"


@pytest.fixture
def sample_version():
    """Sample version range for testing."""
    return "latest"


@pytest.fixture
def sample_pipeline_result() -> Dict[str, Any]:
    """
    Sample pipeline result structure (expected output shape).
    Used to validate actual pipeline output.
    """
    return {
        "package": "lodash",
        "version_range": "latest",
        "generated_at": "2025-11-18T10:00:00.000000",
        "results": [
            {
                "package": "lodash",
                "version_range": "latest",
                "cve_id": "CVE-2025-0869",
                "epss": {
                    "epss_score": None,  # Can be None or float
                    "collected_at": "2025-11-18T10:00:00.000000",
                },
                "cvss": {
                    "cvss_score": None,  # Can be None or float
                    "vector": None,  # Can be None or string
                    "collected_at": "2025-11-18T10:00:00.000000",
                },
                "cases": [
                    {
                        "source": "https://example.com/case",
                        "title": "Example case",
                        "date": "2025-11-18",
                        "summary": "Case summary",
                        "collected_at": "2025-11-18T10:00:00.000000",
                    }
                ],
                "analysis": {
                    "cve_id": "CVE-2025-0869",
                    "risk_level": "Low",  # One of: Low, Medium, High
                    "recommendations": [
                        "Example recommendation 1",
                        "Example recommendation 2",
                    ],
                    "analysis_summary": "Example summary",
                    "generated_at": "2025-11-18T10:00:00.000000",
                },
            }
        ],
    }


@pytest.fixture
async def orchestrator(mock_cache):
    """Create an orchestrator with mocked cache."""
    orch = AgentOrchestrator(cache=mock_cache)
    return orch


def validate_pipeline_output(result: Any) -> bool:
    """
    Validate that pipeline output has the expected shape and types.

    Returns True if valid, raises AssertionError otherwise.
    """
    assert isinstance(result, dict), "Result must be a dict"
    assert "package" in result, "Result must have 'package' key"
    assert "version_range" in result, "Result must have 'version_range' key"
    assert "generated_at" in result, "Result must have 'generated_at' key"
    assert "results" in result, "Result must have 'results' key"
    assert isinstance(result["results"], list), "'results' must be a list"

    for idx, item in enumerate(result["results"]):
        assert isinstance(item, dict), f"Result item {idx} must be a dict"
        assert "cve_id" in item, f"Result item {idx} must have 'cve_id'"
        assert "epss" in item, f"Result item {idx} must have 'epss'"
        assert "cvss" in item, f"Result item {idx} must have 'cvss'"
        assert "cases" in item, f"Result item {idx} must have 'cases'"
        assert "analysis" in item, f"Result item {idx} must have 'analysis'"

        # Validate EPSS structure
        epss = item["epss"]
        assert isinstance(epss, dict), f"epss must be a dict (item {idx})"
        assert "epss_score" in epss, f"epss must have 'epss_score' (item {idx})"
        assert (
            epss["epss_score"] is None or isinstance(epss["epss_score"], (int, float))
        ), f"epss_score must be None or numeric (item {idx})"

        # Validate CVSS structure
        cvss = item["cvss"]
        assert isinstance(cvss, dict), f"cvss must be a dict (item {idx})"
        assert "cvss_score" in cvss, f"cvss must have 'cvss_score' (item {idx})"
        assert (
            cvss["cvss_score"] is None or isinstance(cvss["cvss_score"], (int, float))
        ), f"cvss_score must be None or numeric (item {idx})"
        assert (
            cvss["vector"] is None or isinstance(cvss["vector"], str)
        ), f"vector must be None or string (item {idx})"

        # Validate analysis structure
        analysis = item["analysis"]
        assert isinstance(analysis, dict), f"analysis must be a dict (item {idx})"
        assert "cve_id" in analysis, f"analysis must have 'cve_id' (item {idx})"
        assert "risk_level" in analysis, f"analysis must have 'risk_level' (item {idx})"
        assert analysis["risk_level"] in [
            "Low",
            "Medium",
            "High",
        ], f"risk_level must be Low/Medium/High (item {idx})"
        assert (
            "recommendations" in analysis
        ), f"analysis must have 'recommendations' (item {idx})"
        assert isinstance(
            analysis["recommendations"], list
        ), f"recommendations must be a list (item {idx})"

    return True
