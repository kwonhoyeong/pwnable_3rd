"""GPT-5 API 클라이언트 구현(GPT-5 API client implementation)."""
from __future__ import annotations

from typing import Any, Dict

import httpx

from ..config import get_settings
from ..logger import get_logger
from .base import IAIClient

logger = get_logger(__name__)


class GPT5Client(IAIClient):
    """GPT-5 API 래퍼(Wrapper for GPT-5 API)."""

    def __init__(self, base_url: str = "https://api.openai.com/v1", timeout: float = 300.0) -> None:
        settings = get_settings()
        self._base_url = base_url
        self._api_key = settings.gpt5_api_key
        self._timeout = timeout

    async def chat(self, prompt: str, **kwargs: Any) -> str:
        """GPT-5 채팅 호출(Invoke GPT-5 chat)."""

        headers = {"Authorization": f"Bearer {self._api_key}"}
        payload = {"prompt": prompt, **kwargs}
        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""
        except httpx.HTTPStatusError as exc:  # pragma: no cover - skeleton fallback
            logger.warning("GPT-5 API HTTP 오류(HTTP error): %s", exc)
            logger.debug("GPT-5 failure details", exc_info=exc)
            raise RuntimeError(f"GPT-5 API HTTP error: {exc}") from exc
        except httpx.HTTPError as exc:  # pragma: no cover - skeleton fallback
            logger.warning("GPT-5 API 네트워크 오류(Network error): %s", exc)
            logger.debug("GPT-5 failure details", exc_info=exc)
            raise RuntimeError(f"GPT-5 API network error: {exc}") from exc

    async def structured_output(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """GPT-5 구조화 응답(Structured response from GPT-5)."""

        response_text = await self.chat(prompt, schema=schema)
        return {"raw": response_text}
