"""
Regression Test Suite
Verifies fixes from major refactoring sprint:
1. API Key authentication enforcement
2. Stats endpoint UPPERCASE key consistency
3. CVSS fetcher NVD-first strategy
4. Multi-Ecosystem Support
"""
import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# Add project root to sys.path to allow imports from services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from common_lib.config import get_settings
from datetime import datetime


# ============================================================================
# TEST 1: API Key Authentication
# ============================================================================

@pytest.mark.asyncio
async def test_api_auth_missing_key_returns_401_or_403():
    """
    Verify that requests without X-API-Key header are rejected.
    Expected: 401 or 403 status code
    """
    async with httpx.AsyncClient(base_url="http://localhost:8004") as client:
        # Request without API key header
        response = await client.get("/api/v1/stats")
        
        # Should be rejected (either 401 Unauthorized or 403 Forbidden)
        assert response.status_code in [401, 403], \
            f"Expected 401/403 for missing API key, got {response.status_code}"


@pytest.mark.asyncio
async def test_api_auth_with_valid_key_returns_200():
    """
    Verify that requests with valid X-API-Key header are accepted.
    Expected: 200 status code
    """
    async with httpx.AsyncClient(base_url="http://localhost:8004") as client:
        # Request with valid API key header
        headers = {"X-API-Key": "dev-api-key-123"}
        response = await client.get("/api/v1/stats", headers=headers)
        
        # Should be accepted
        assert response.status_code == 200, \
            f"Expected 200 with valid API key, got {response.status_code}"


# ============================================================================
# TEST 2: Stats Endpoint UPPERCASE Keys
# ============================================================================

@pytest.mark.asyncio
async def test_stats_endpoint_uppercase_keys():
    """
    Verify that /api/v1/stats returns risk_distribution with UPPERCASE keys.
    This ensures the KeyError fix (Unknown -> UNKNOWN) is working.
    Expected: JSON with CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN keys
    """
    async with httpx.AsyncClient(base_url="http://localhost:8004") as client:
        headers = {"X-API-Key": "dev-api-key-123"}
        response = await client.get("/api/v1/stats", headers=headers)
        
        assert response.status_code == 200, \
            f"Stats endpoint returned {response.status_code}"
        
        data = response.json()
        
        # Verify risk_distribution exists and has UPPERCASE keys
        assert "risk_distribution" in data, "Missing risk_distribution in response"
        
        risk_dist = data["risk_distribution"]
        required_keys = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"}
        
        for key in required_keys:
            assert key in risk_dist, \
                f"Missing UPPERCASE key '{key}' in risk_distribution. Found: {list(risk_dist.keys())}"
        
        # Verify values are integers
        for key, value in risk_dist.items():
            assert isinstance(value, (int, float)), \
                f"risk_distribution[{key}] should be numeric, got {type(value)}"


# ============================================================================
# TEST 3: CVSS Fetcher NVD-First Strategy (Unit Test)
# ============================================================================

@pytest.mark.asyncio
async def test_cvss_fetcher_nvd_success():
    """
    Verify that fetch_score calls NVD API first and returns NVD data on success.
    Uses mock to avoid actual API calls.
    """
    from cvss_fetcher.app.service import CVSSService

    # Mock successful NVD response
    mock_nvd_response = {
        "vulnerabilities": [{
            "cve": {
                "metrics": {
                    "cvssMetricV31": [{
                        "cvssData": {
                            "baseScore": 9.8,
                            "vectorString": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
                        }
                    }]
                }
            }
        }]
    }

    service = CVSSService()

    with patch("httpx.AsyncClient") as MockClient:
        # Setup mock
        mock_client_instance = AsyncMock()
        mock_response = MagicMock() # Use MagicMock for synchronous methods like .json()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_nvd_response
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        MockClient.return_value = mock_client_instance

        # Execute
        result = await service.fetch_score("CVE-2023-12345")

        # Verify NVD was called and result is correct
        assert result["source"] == "NVD", "Should use NVD source"
        assert result["cvss_score"] == 9.8
        assert result["vector"] == "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"

@pytest.mark.asyncio
async def test_cvss_fetcher_nvd_failure_fallback():
    """
    Verify that fetch_score falls back to Perplexity when NVD fails.
    Uses mock to simulate NVD 404 error.
    """
    from cvss_fetcher.app.service import CVSSService

    service = CVSSService()

    # Mock Perplexity client
    service._perplexity = AsyncMock()
    # Mock structured_output instead of chat, returning a dict with 'raw' key containing the JSON string
    service._perplexity.structured_output.return_value = {
        "raw": '{"score": 7.5, "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N"}'
    }

    with patch("httpx.AsyncClient") as MockClient:
        # Setup mock to fail NVD
        mock_client_instance = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError("404 Not Found", request=None, response=mock_response)
        mock_client_instance.get.return_value = mock_response
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.__aexit__.return_value = None
        MockClient.return_value = mock_client_instance

        # Execute
        result = await service.fetch_score("CVE-2023-12345")

        # Verify fallback to Perplexity
        assert result["source"] == "Perplexity", "Should fallback to Perplexity"
        assert result["cvss_score"] == 7.5


# ============================================================================
# TEST 4: Multi-Ecosystem Support
# ============================================================================

@pytest.mark.asyncio
async def test_query_service_ecosystem_propagation():
    """
    Verify that QueryService passes the ecosystem parameter to redis_ops.submit_analysis_job.
    """
    from query_api.app.service import QueryService
    from common_lib.errors import ResourceNotFound
    
    service = QueryService()
    
    # Mock repository to raise ResourceNotFound
    mock_repo = AsyncMock()
    mock_repo.find_by_package.side_effect = ResourceNotFound(resource_type="package", identifier="django")
    
    # Mock redis_ops.submit_analysis_job
    with patch("query_api.app.service.submit_analysis_job", new_callable=AsyncMock) as mock_submit:
        mock_submit.return_value = True
        
        # Mock _poll_for_analysis_results to return immediately (or timeout immediately)
        # We just want to check the submit call
        with patch.object(service, "_poll_for_analysis_results", new_callable=AsyncMock) as mock_poll:
            mock_poll.return_value = None # Simulate timeout/no results yet
            
            # Execute query with ecosystem='pip'
            try:
                await service.query(
                    repository=mock_repo,
                    package="django",
                    cve_id=None,
                    version="latest",
                    ecosystem="pip"
                )
            except Exception:
                # Expect AnalysisInProgressError or similar, but we only care about the submit call
                pass
            
            # Verify submit_analysis_job was called with ecosystem='pip'
            mock_submit.assert_called_once()
            call_kwargs = mock_submit.call_args.kwargs
            assert call_kwargs["package_name"] == "django"
            assert call_kwargs["ecosystem"] == "pip"
            assert call_kwargs["version"] == "latest"


# ============================================================================
# TEST 5: Worker DLQ (Integration Test - Optional)
# ============================================================================

@pytest.mark.skipif(
    True,  # Skip by default; enable for integration testing
    reason="Requires running Redis and worker service"
)
@pytest.mark.asyncio
async def test_worker_dlq_on_failure():
    """
    Integration test: Verify that failed tasks are pushed to DLQ.
    This test requires Redis to be running.
    """
    import redis.asyncio as redis
    import json
    
    r = await redis.from_url("redis://localhost:6379/0", decode_responses=True)
    
    # Clear DLQ before test
    await r.delete("analysis_tasks:failed")
    
    # Push a malformed task (will cause processing failure)
    bad_task = json.dumps({"invalid": "task"})
    await r.rpush("analysis_tasks", bad_task)
    
    # Wait for worker to process (adjust sleep time as needed)
    import asyncio
    await asyncio.sleep(5)
    
    # Check DLQ
    dlq_length = await r.llen("analysis_tasks:failed")
    assert dlq_length > 0, "Failed task should be in DLQ"
    
    # Verify failed task has error metadata
    failed_payload = await r.lpop("analysis_tasks:failed")
    failed_task = json.loads(failed_payload)
    
    assert "error_msg" in failed_task, "DLQ task should have error_msg"
    assert "error_timestamp" in failed_task, "DLQ task should have error_timestamp"
    
    await r.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
