"""GPT-5 API 클라이언트 구현(GPT-5 API client implementation)."""
from __future__ import annotations

import asyncio
import os
from typing import Any, Dict

import httpx

from ..config import get_settings
from ..logger import get_logger
from ..retry_config import get_retry_decorator
from .base import IAIClient

logger = get_logger(__name__)


class GPT5Client(IAIClient):
    """GPT-5 API 래퍼(Wrapper for GPT-5 API)."""

    def __init__(self, base_url: str = "https://api.openai.com/v1", timeout: float = 60.0) -> None:
        settings = get_settings()
        self._base_url = base_url
        self._api_key = settings.gpt5_api_key
        self._timeout = timeout
        self._allow_external = settings.allow_external_calls
        self._default_model = os.getenv("NT_GPT5_MODEL", "gpt-5.1")

        # Validate API key at initialization
        if not self._api_key or self._api_key.strip() == "":
            logger.error(
                "NT_GPT5_API_KEY is not set or empty. "
                "GPT-5 analysis will fail and use fallback responses. "
                "Please set NT_GPT5_API_KEY in your .env file."
            )

    @get_retry_decorator()
    async def chat(self, prompt: str, **kwargs: Any) -> str:
        """GPT-5 채팅 호출(Invoke GPT-5 chat)."""

        # Check API key before making request
        if not self._allow_external:
            logger.info("GPT-5 external calls disabled; using fallback responses.")
            raise RuntimeError("GPT-5 API disabled by configuration")

        if not self._api_key or self._api_key.strip() == "":
            logger.warning(
                "NT_GPT5_API_KEY is missing or empty; skipping GPT-5 API call and using fallback analysis."
            )
            raise RuntimeError("NT_GPT5_API_KEY is not configured")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": kwargs.pop("model", self._default_model),
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

        logger.debug(
            "Making GPT-5 API request to %s/chat/completions",
            self._base_url
        )

        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                request = client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response = await asyncio.wait_for(request, timeout=self._timeout)
                response.raise_for_status()
                data = response.json()
            choices = data.get("choices", [])
            if choices:
                logger.info("GPT-5 API call succeeded")
                return choices[0].get("message", {}).get("content", "")
            logger.warning("GPT-5 API returned empty choices")
            return ""
        except asyncio.TimeoutError as exc:
            logger.info(
                "GPT-5 API request timed out after %.1fs (endpoint=%s/chat/completions); using fallback.",
                self._timeout,
                self._base_url,
            )
            raise RuntimeError("GPT-5 API timeout") from exc
        except httpx.HTTPStatusError as exc:  # pragma: no cover - skeleton fallback
            status_code = exc.response.status_code
            try:
                error_body = exc.response.text
            except Exception:
                error_body = "<unable to read response body>"

            logger.error(
                "GPT-5 API HTTP error: status=%d, endpoint=%s/chat/completions, error_body=%s",
                status_code,
                self._base_url,
                error_body,
                exc_info=True
            )

            if status_code == 401:
                logger.error(
                    "GPT-5 API authentication failed (401). "
                    "Please check that NT_GPT5_API_KEY is valid."
                )
            elif status_code == 400:
                logger.error(
                    "GPT-5 API bad request (400). "
                    "The request payload may be invalid or the API key may be incorrect."
                )

            raise RuntimeError(f"GPT-5 API HTTP error: status={status_code}, body={error_body}") from exc
        except httpx.HTTPError as exc:  # pragma: no cover - skeleton fallback
            logger.info(
                "GPT-5 API network error: endpoint=%s/chat/completions. Falling back.",
                self._base_url,
            )
            logger.debug("GPT-5 network error details", exc_info=exc)
            raise RuntimeError(f"GPT-5 API network error: {exc}") from exc

    async def structured_output(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """GPT-5 구조화 응답(Structured response from GPT-5)."""

        response_text = await self.chat(prompt, schema=schema)
        return {"raw": response_text}
