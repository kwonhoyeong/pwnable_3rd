"""Claude API 클라이언트 구현(Claude API client implementation)."""
from __future__ import annotations

from typing import Any, Dict

import httpx

from ..config import get_settings
from ..logger import get_logger
from .base import IAIClient

logger = get_logger(__name__)


class ClaudeClient(IAIClient):
    """Claude API 래퍼(Wrapper for Claude API)."""

    def __init__(self, base_url: str = "https://api.anthropic.com/v1") -> None:
        settings = get_settings()
        self._base_url = base_url
        self._api_key = settings.claude_api_key
        self._timeout = 30.0

    async def chat(self, prompt: str, **kwargs: Any) -> str:
        """Claude 채팅 호출(Invoke Claude chat)."""

        if not self._api_key:
            raise RuntimeError("Claude API key is not configured")

        headers = {
            "x-api-key": self._api_key,
            "Accept": "application/json",
        }
        payload = {"prompt": prompt, **kwargs}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/messages",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:  # pragma: no cover - skeleton
            logger.exception("Claude API error", exc_info=exc)
            raise

        return data.get("completion", "")

    async def structured_output(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Claude 구조화 응답(Structured response from Claude)."""

        response_text = await self.chat(prompt, schema=schema)
        return {"raw": response_text}
