"""CVSS API 호출 서비스(Service for CVSS API calls)."""
from __future__ import annotations

import asyncio
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from common_lib.ai_clients import PerplexityClient
from common_lib.config import get_settings
from common_lib.logger import get_logger

logger = get_logger(__name__)


class CVSSService:
    """CVSS 점수 조회 서비스(Service fetching CVSS scores from NVD)."""

    NVD_API_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

    def __init__(self, timeout: float = 10.0, max_retries: int = 2) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._allow_external = get_settings().allow_external_calls
        
        # NVD API 키 가져오기
        self._nvd_api_key = os.getenv("NVD_API_KEY")
        
        if not self._nvd_api_key:
            logger.warning("NVD API 키가 설정되지 않음 - 제한된 속도로 실행됩니다 (API key not set - running with rate limits)")

        # Perplexity Client 초기화 (Fallback용)
        self._perplexity = PerplexityClient()

    @staticmethod
    def _build_response(
        cve_id: str,
        score: Optional[float] = None,
        vector: Optional[str] = None,
        description: Optional[str] = None,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:
        return {
            "cve_id": cve_id,
            "cvss_score": score,
            "vector": vector,
            "description": description,
            "source": source,
            "collected_at": datetime.utcnow(),
        }

    def _validate_cve_id(self, cve_id: str) -> bool:
        """CVE ID 형식 검증(Validate CVE ID format)."""
        pattern = r"^CVE-\d{4}-\d{4,}$"
        return bool(re.match(pattern, cve_id))

    async def _fetch_from_perplexity(self, cve_id: str) -> Dict[str, Any]:
        """Perplexity를 통해 CVSS 점수 검색(Search CVSS score via Perplexity)."""
        logger.info("Perplexity로 CVSS 점수 검색 시도(Attempting Perplexity fallback for %s)", cve_id)
        
        prompt = (
            f"Find the CVSS v3.1 (or v3.0/v2) base score and vector string for {cve_id}. "
            "Return ONLY the JSON object with keys: 'score' (float) and 'vector' (string). "
            "If not found, return empty JSON {}."
        )
        
        try:
            # 구조화된 출력 요청 (Structured output request)
            schema = {
                "type": "object",
                "properties": {
                    "score": {"type": "number"},
                    "vector": {"type": "string"}
                },
                "required": ["score"]
            }
            
            result = await self._perplexity.structured_output(prompt, schema)
            
            # 파싱 (Parsing logic depends on actual client implementation, assuming raw text needs parsing or direct dict)
            # For now, let's assume the client returns a dict with 'raw' text or we parse the text.
            # Since structured_output returns {'raw': str}, we might need to parse it if it's not automatically parsed.
            # But let's try to use a simpler chat approach if structured is complex, 
            # or assume the user wants the text parsed.
            # Let's use a simple regex on the chat response for robustness.
            
            response_text = result.get("raw", "")
            
            # Extract score
            score_match = re.search(r'"score":\s*([\d\.]+)', response_text)
            vector_match = re.search(r'"vector":\s*"([^"]+)"', response_text)
            
            score = float(score_match.group(1)) if score_match else None
            vector = vector_match.group(1) if vector_match else None
            
            if score is not None:
                logger.info("Perplexity에서 CVSS 점수 발견(Found CVSS via Perplexity): %s = %.1f", cve_id, score)
                return self._build_response(cve_id, score=score, vector=vector, source="Perplexity")
            
        except Exception as exc:
            logger.warning("Perplexity 검색 실패(Perplexity fallback failed): %s", exc)
            
        return self._build_response(cve_id, source="not_found_perplexity")

    async def fetch_score(self, cve_id: str) -> Dict[str, Any]:
        """NVD API를 통해 CVSS 점수를 조회하고, 실패 시 Perplexity로 폴백(Fetch CVSS score from NVD API with Perplexity fallback)."""

        if not self._allow_external:
            logger.info("외부 CVSS 조회 비활성화됨(External CVSS lookups disabled); returning fallback score.")
            return self._build_response(cve_id)

        if not self._validate_cve_id(cve_id):
            logger.warning("Invalid CVE ID format: %s", cve_id)
            return self._build_response(cve_id)

        # NVD API 헤더 설정
        headers = {}
        if self._nvd_api_key:
            headers["apiKey"] = self._nvd_api_key
            logger.debug("Using NVD API key for request")

        params = {"cveId": cve_id}

        for attempt in range(1, self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    logger.info("Attempting NVD API request for %s (attempt %d/%d)", cve_id, attempt, self._max_retries)
                    response = await client.get(
                        self.NVD_API_URL,
                        headers=headers,
                        params=params,
                    )
                    
                    # Handle 404 - CVE not found in NVD
                    if response.status_code == 404:
                        logger.warning("NVD fetch failed for %s: CVE not found (404), falling back to Perplexity", cve_id)
                        return await self._fetch_from_perplexity(cve_id)
                    
                    # Handle authentication errors
                    if response.status_code == 403:
                        logger.warning("NVD API authentication failed (403) - check API key")
                        if attempt == self._max_retries:
                            logger.warning("NVD fetch failed for %s after %d attempts, falling back to Perplexity", cve_id, self._max_retries)
                            return await self._fetch_from_perplexity(cve_id)
                        continue
                    
                    # Raise for other HTTP errors
                    response.raise_for_status()
                    data = response.json()

                    # Parse NVD response for CVSS data
                    if "vulnerabilities" in data and len(data["vulnerabilities"]) > 0:
                        vuln = data["vulnerabilities"][0]
                        cve_data = vuln.get("cve", {})
                        
                        # Extract CVSS metrics (priority: v3.1 > v3.0 > v2)
                        metrics = cve_data.get("metrics", {})
                        cvss_score = None
                        vector = None
                        cvss_version = None
                        
                        # Try CVSS v3.1 first
                        if "cvssMetricV31" in metrics and len(metrics["cvssMetricV31"]) > 0:
                            cvss_data = metrics["cvssMetricV31"][0]["cvssData"]
                            cvss_score = cvss_data.get("baseScore")
                            vector = cvss_data.get("vectorString")
                            cvss_version = "3.1"
                        # Fall back to CVSS v3.0
                        elif "cvssMetricV30" in metrics and len(metrics["cvssMetricV30"]) > 0:
                            cvss_data = metrics["cvssMetricV30"][0]["cvssData"]
                            cvss_score = cvss_data.get("baseScore")
                            vector = cvss_data.get("vectorString")
                            cvss_version = "3.0"
                        # Last resort: CVSS v2
                        elif "cvssMetricV2" in metrics and len(metrics["cvssMetricV2"]) > 0:
                            cvss_data = metrics["cvssMetricV2"][0]["cvssData"]
                            cvss_score = cvss_data.get("baseScore")
                            vector = cvss_data.get("vectorString")
                            cvss_version = "2.0"

                        # Extract Description (English)
                        description = None
                        if "descriptions" in cve_data:
                            for desc in cve_data["descriptions"]:
                                if desc.get("lang") == "en":
                                    description = desc.get("value")
                                    break

                        if cvss_score is not None:
                            logger.info(
                                "Successfully fetched CVSS from NVD: %s = %.1f (version %s, attempt %d)",
                                cve_id,
                                cvss_score,
                                cvss_version,
                                attempt,
                            )
                            return {
                                "cve_id": cve_id,
                                "cvss_score": float(cvss_score),
                                "vector": vector,
                                "description": description,
                                "source": "NVD",
                                "collected_at": datetime.utcnow(),
                            }
                        else:
                            logger.warning("NVD response contains no CVSS data for %s", cve_id)
                            if attempt == self._max_retries:
                                logger.warning("NVD fetch failed for %s, falling back to Perplexity", cve_id)
                                return await self._fetch_from_perplexity(cve_id)

                    else:
                        logger.warning("NVD response contains no vulnerability data for %s", cve_id)
                        if attempt == self._max_retries:
                            logger.warning("NVD fetch failed for %s, falling back to Perplexity", cve_id)
                            return await self._fetch_from_perplexity(cve_id)

            except httpx.TimeoutException:
                logger.warning(
                    "NVD API timeout for %s (attempt %d/%d)",
                    cve_id,
                    attempt,
                    self._max_retries,
                )
                if attempt == self._max_retries:
                    logger.warning("NVD fetch failed for %s after timeout, falling back to Perplexity", cve_id)
                    return await self._fetch_from_perplexity(cve_id)
                    
            except httpx.HTTPError as exc:
                logger.error(
                    "NVD API HTTP error for %s (attempt %d/%d): %s",
                    cve_id,
                    attempt,
                    self._max_retries,
                    exc,
                )
                if attempt == self._max_retries:
                    logger.warning("NVD fetch failed for %s, falling back to Perplexity", cve_id)
                    return await self._fetch_from_perplexity(cve_id)
                    
            except Exception as exc:
                logger.error(
                    "Unexpected error fetching from NVD for %s (attempt %d/%d): %s",
                    cve_id,
                    attempt,
                    self._max_retries,
                    exc,
                    exc_info=True,
                )
                if attempt == self._max_retries:
                    logger.warning("NVD fetch failed for %s, falling back to Perplexity", cve_id)
                    return await self._fetch_from_perplexity(cve_id)

        # Final fallback if all retries exhausted
        logger.warning("All NVD attempts exhausted for %s, falling back to Perplexity", cve_id)
        return await self._fetch_from_perplexity(cve_id)
