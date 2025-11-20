"""Claude API 클라이언트 구현(Claude API client implementation)."""
from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List

from anthropic import Anthropic

from ..config import get_settings
from ..logger import get_logger
from ..retry_config import get_retry_decorator
from .base import IAIClient

logger = get_logger(__name__)


class ClaudeClient(IAIClient):
    """Claude API 래퍼(Wrapper for Claude API using Anthropic SDK)."""

    def __init__(self, timeout: float = 5.0) -> None:
        settings = get_settings()
        self._api_key = settings.claude_api_key
        self._timeout = timeout
        self._allow_external = settings.allow_external_calls
        self._default_model = os.getenv("NT_CLAUDE_MODEL", "claude-sonnet-4-5")
        self._default_max_tokens = 1024
        # Initialize Anthropic client (API key loaded from ANTHROPIC_API_KEY env var automatically)
        self._client = Anthropic(api_key=self._api_key) if self._api_key else Anthropic()
        if not self._api_key or self._api_key.strip() == "":
            logger.error(
                "NT_CLAUDE_API_KEY or ANTHROPIC_API_KEY is not set or empty. Claude-powered summaries will fall back to defaults."
            )

    @get_retry_decorator()
    async def chat(self, prompt: str, **kwargs: Any) -> str:
        """Claude 채팅 호출(Invoke Claude chat using Anthropic SDK)."""

        if not self._allow_external:
            logger.info(
                "Claude external calls disabled (set NT_ALLOW_EXTERNAL_CALLS=true to enable)."
            )
            raise RuntimeError("Claude API disabled by configuration: NT_ALLOW_EXTERNAL_CALLS=false")

        if not self._api_key or self._api_key.strip() == "":
            raise RuntimeError("NT_CLAUDE_API_KEY or ANTHROPIC_API_KEY is not configured")

        try:
            # Extract parameters from kwargs, with defaults
            model = kwargs.pop("model", self._default_model)
            max_tokens = kwargs.pop("max_tokens", self._default_max_tokens)
            messages = kwargs.pop(
                "messages",
                [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )

            # Call Claude API using Anthropic SDK (synchronously wrapped)
            response = await asyncio.to_thread(
                self._client.messages.create,
                model=model,
                max_tokens=max_tokens,
                messages=messages,
                **kwargs
            )

            # Extract text from response
            content = response.content
            if isinstance(content, list):
                texts: List[str] = []
                for block in content:
                    if hasattr(block, "text"):  # TextBlock
                        texts.append(block.text)
                return "\n".join(texts).strip()
            return ""
        except asyncio.TimeoutError as exc:
            logger.info("Claude API 요청 시간 초과(Request timed out); falling back.")
            raise RuntimeError("Claude API timeout") from exc
        except Exception as exc:  # pragma: no cover - skeleton fallback
            logger.warning("Claude API 오류(Error): %s", exc)
            logger.debug("Claude failure details", exc_info=exc)
            raise RuntimeError(f"Claude API error: {exc}") from exc

    async def structured_output(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Claude 구조화 응답(Structured response from Claude using Anthropic SDK)."""

        # Note: schema parameter can be passed to the API if implementing JSON mode
        response_text = await self.chat(prompt)
        return {"raw": response_text}
