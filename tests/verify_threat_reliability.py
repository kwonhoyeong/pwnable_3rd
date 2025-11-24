import asyncio
from unittest.mock import MagicMock, patch
from threat_agent.app.services import ThreatSearchService, ThreatAggregationService, ThreatInput, ThreatCase

async def verify_reliability():
    print("--- Testing ThreatAgent Reliability ---")

    # 1. Test Search Failure
    print("\n1. Testing Search Failure (Graceful Degradation)...")
    with patch("threat_agent.app.services.PerplexityClient") as MockPerplexity:
        # Setup mock to raise exception
        mock_client = MockPerplexity.return_value
        mock_client.chat.side_effect = Exception("Simulated Perplexity API Error")
        
        service = ThreatSearchService()
        payload = ThreatInput(cve_id="CVE-TEST-001", package="test-pkg", version_range="1.0.0")
        
        results = await service.search_cases(payload)
        
        if results == []:
            print("PASS: Search service returned empty list on failure.")
        else:
            print(f"FAIL: Search service returned {results} instead of empty list.")

    # 2. Test Summary Failure
    print("\n2. Testing Summary Failure (Partial Success)...")
    with patch("threat_agent.app.services.ThreatSearchService") as MockSearchService, \
         patch("threat_agent.app.services.ClaudeClient") as MockClaude:
        
        # Setup mock search to return a case (async)
        mock_search = MockSearchService.return_value
        # Make search_cases an async mock that returns the list
        future = asyncio.Future()
        future.set_result([
            ThreatCase(
                source="http://example.com",
                title="Test Threat",
                date="2025-01-01",
                summary="Original summary",
                collected_at="2025-01-01T00:00:00"
            )
        ])
        mock_search.search_cases.return_value = future
        
        # Setup mock summary to raise exception
        mock_claude = MockClaude.return_value
        mock_claude.chat.side_effect = Exception("Simulated Claude API Error")
        
        service = ThreatAggregationService()
        # Inject mocked search service
        service._search = mock_search
        
        payload = ThreatInput(cve_id="CVE-TEST-002", package="test-pkg", version_range="1.0.0")
        
        response = await service.collect(payload)
        
        if len(response.cases) == 1:
            summary = response.cases[0].summary
            if "AI 요약 생성 실패" in summary:
                print("PASS: Aggregation service returned case with fallback summary.")
            else:
                print(f"FAIL: Summary does not contain fallback text. Got: {summary[:50]}...")
        else:
            print(f"FAIL: Aggregation service returned {len(response.cases)} cases instead of 1.")

if __name__ == "__main__":
    asyncio.run(verify_reliability())
