"""Claude API 클라이언트 구현(Claude API client implementation)."""
from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List

import httpx

from ..config import get_settings
from ..logger import get_logger
from .base import IAIClient

logger = get_logger(__name__)


class ClaudeClient(IAIClient):
    """Claude API 래퍼(Wrapper for Claude API)."""

    def __init__(self, base_url: str = "https://api.anthropic.com/v1", timeout: float = 5.0) -> None:
        settings = get_settings()
        self._base_url = base_url.rstrip("/")
        self._api_key = settings.claude_api_key
        self._timeout = timeout
        self._allow_external = settings.allow_external_calls
        self._default_model = os.getenv("NT_CLAUDE_MODEL", "claude-3-5-sonnet-20240620")
        self._default_max_tokens = 1024
        self._api_version = os.getenv("NT_CLAUDE_API_VERSION", "2023-06-01")
        if not self._api_key or self._api_key.strip() == "":
            logger.error(
                "NT_CLAUDE_API_KEY is not set or empty. Claude-powered summaries will fall back to defaults."
            )

    async def chat(self, prompt: str, **kwargs: Any) -> str:
        """Claude 채팅 호출(Invoke Claude chat)."""

        if not self._allow_external:
            logger.info(
                "Claude external calls disabled (set NT_ALLOW_EXTERNAL_CALLS=true to enable)."
            )
            raise RuntimeError("Claude API disabled by configuration: NT_ALLOW_EXTERNAL_CALLS=false")

        if not self._api_key or self._api_key.strip() == "":
            raise RuntimeError("NT_CLAUDE_API_KEY is not configured")

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": self._api_version,
            "content-type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": kwargs.pop("model", self._default_model),
            "max_tokens": kwargs.pop("max_tokens", self._default_max_tokens),
            "messages": kwargs.pop(
                "messages",
                [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            ),
        }
        payload.update(kwargs)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/messages",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
            content = data.get("content")
            if isinstance(content, list):
                texts: List[str] = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            texts.append(block.get("text", ""))
                return "\n".join(texts).strip()
            if isinstance(content, str):
                return content
            return ""
        except asyncio.TimeoutError as exc:
            logger.info("Claude API 요청 시간 초과(Request timed out after %.1fs); falling back.", self._timeout)
            raise RuntimeError("Claude API timeout") from exc
        except httpx.HTTPStatusError as exc:  # pragma: no cover - skeleton fallback
            logger.warning("Claude API HTTP 오류(HTTP error): %s", exc)
            logger.debug("Claude failure details", exc_info=exc)
            raise RuntimeError(f"Claude API HTTP error: {exc}") from exc
        except httpx.HTTPError as exc:  # pragma: no cover - skeleton fallback
            logger.info("Claude API 네트워크 오류(Network error); falling back.")
            logger.debug("Claude failure details", exc_info=exc)
            raise RuntimeError(f"Claude API network error: {exc}") from exc

    async def structured_output(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Claude 구조화 응답(Structured response from Claude)."""

        response_text = await self.chat(prompt, schema=schema)
        return {"raw": response_text}
