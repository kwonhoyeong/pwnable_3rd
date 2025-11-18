"""Perplexity API 클라이언트 구현(Perplexity API client implementation)."""
from __future__ import annotations

import asyncio
from typing import Any, Dict

import httpx

from ..config import get_settings
from ..logger import get_logger
from .base import IAIClient

logger = get_logger(__name__)


class PerplexityClient(IAIClient):
    """Perplexity API 래퍼(Wrapper for Perplexity API)."""

    def __init__(self, base_url: str = "https://api.perplexity.ai", timeout: float = 5.0) -> None:
        settings = get_settings()
        self._base_url = base_url
        self._api_key = settings.perplexity_api_key
        self._timeout = timeout
        self._allow_external = settings.allow_external_calls

        # Log warning at initialization for early visibility, but allow fallback mechanism
        if not self._api_key or self._api_key.strip() == "":
            logger.warning("Perplexity API 키가 설정되지 않음 - 폴백 모드로 실행됩니다(API key not set - will use fallback mode)")

    async def chat(self, prompt: str, **kwargs: Any) -> str:
        """Perplexity 검색 호출(Invoke Perplexity search)."""

        # Check API key and raise error to trigger fallback mechanism
        if not self._allow_external:
            raise RuntimeError("Perplexity API disabled by configuration")

        if not self._api_key or self._api_key.strip() == "":
            raise RuntimeError("Perplexity API key is not configured")

        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {"query": prompt, **kwargs}
        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                request = client.post(f"{self._base_url}/search", headers=headers, json=payload)
                response = await asyncio.wait_for(request, timeout=self._timeout)
                response.raise_for_status()
                data = response.json()
            return data.get("answer", "")
        except asyncio.TimeoutError as exc:
            logger.info("Perplexity API 요청 시간 초과(Request timed out after %.1fs); falling back.", self._timeout)
            raise RuntimeError("Perplexity API timeout") from exc
        except httpx.HTTPStatusError as exc:  # pragma: no cover - skeleton fallback
            logger.warning("Perplexity API HTTP 오류(HTTP error): %s", exc)
            logger.debug("Perplexity failure details", exc_info=exc)
            raise RuntimeError(f"Perplexity API HTTP error: {exc}") from exc
        except httpx.HTTPError as exc:  # pragma: no cover - skeleton fallback
            logger.info("Perplexity API 네트워크 오류(Network error); falling back.")
            logger.debug("Perplexity failure details", exc_info=exc)
            raise RuntimeError(f"Perplexity API network error: {exc}") from exc

    async def structured_output(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Perplexity 구조화 응답(Structured response from Perplexity)."""

        response_text = await self.chat(prompt, schema=schema)
        return {"raw": response_text}
