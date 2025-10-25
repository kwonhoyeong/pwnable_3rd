"""Perplexity API 클라이언트 구현(Perplexity API client implementation)."""
from __future__ import annotations

from typing import Any, Dict

import httpx

from ..config import get_settings
from ..logger import get_logger
from .base import IAIClient

logger = get_logger(__name__)


class PerplexityClient(IAIClient):
    """Perplexity API 래퍼(Wrapper for Perplexity API)."""

    def __init__(self, base_url: str = "https://api.perplexity.ai") -> None:
        settings = get_settings()
        self._base_url = base_url
        self._api_key = settings.perplexity_api_key
        self._timeout = 30.0

    async def chat(self, prompt: str, **kwargs: Any) -> str:
        """Perplexity 검색 호출(Invoke Perplexity search)."""

        if not self._api_key:
            raise RuntimeError("Perplexity API key is not configured")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }
        payload = {"query": prompt, **kwargs}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/search",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:  # pragma: no cover - skeleton
            logger.exception("Perplexity API error", exc_info=exc)
            raise

        return data.get("answer", "")

    async def structured_output(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Perplexity 구조화 응답(Structured response from Perplexity)."""

        response_text = await self.chat(prompt, schema=schema)
        return {"raw": response_text}
