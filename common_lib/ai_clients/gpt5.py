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

        # Extract parameters from kwargs
        model = kwargs.pop("model", self._default_model)
        temperature = kwargs.pop("temperature", 0.7)
        max_tokens = kwargs.pop("max_tokens", 4096)
        system_prompt = kwargs.pop("system", None)

        # Build messages array - OpenAI requires system message in messages, not as separate parameter
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_completion_tokens": max_tokens,  # Changed from max_tokens to max_completion_tokens
        }

        # Check API key and raise error to trigger fallback mechanism
        if not self._allow_external:
            raise RuntimeError("GPT-5 API disabled by configuration")

        if not self._api_key or self._api_key.strip() == "":
            raise RuntimeError("GPT-5 API key is not configured")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
                logger.debug("Sending GPT-5 API request to %s with model %s", self._base_url, model)
                response = await client.post(
                    f"{self._base_url}/chat/completions", headers=headers, json=payload
                )

                # Log response status for debugging
                logger.debug("GPT-5 API response status: %s", response.status_code)

                if response.status_code != 200:
                    error_body = response.text
                    logger.error(
                        "GPT-5 API HTTP error: status=%s, endpoint=%s, error_body=%s",
                        response.status_code,
                        f"{self._base_url}/chat/completions",
                        error_body,
                    )

                    if response.status_code == 400:
                        logger.error(
                            "GPT-5 API bad request (400). The request payload may be invalid or the API key may be incorrect."
                        )
                    elif response.status_code == 401:
                        logger.error("GPT-5 API unauthorized (401). Check your API key.")
                    elif response.status_code == 429:
                        logger.warning("GPT-5 API rate limit exceeded (429). Retrying may help.")

                response.raise_for_status()
                data = response.json()

            # Extract content from GPT response
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if content:
                logger.info("GPT-5 API call succeeded")
                return content
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
