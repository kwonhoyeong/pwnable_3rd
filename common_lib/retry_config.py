"""재시도 로직 설정 및 유틸리티(Retry logic configuration and utilities)."""
from __future__ import annotations

from typing import Any, Callable

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)


def _is_retryable_exception(exc: BaseException) -> bool:
    """재시도 가능한 예외인지 확인(Check if exception is retryable).

    Retryable exceptions:
    - httpx.ConnectError: Network connection errors
    - httpx.ReadTimeout: Request timeout
    - httpx.HTTPStatusError with status 5xx: Server errors

    Non-retryable exceptions:
    - httpx.HTTPStatusError with status 401/400: Client errors
    """
    if isinstance(exc, httpx.ConnectError):
        return True

    if isinstance(exc, httpx.ReadTimeout):
        return True

    if isinstance(exc, httpx.HTTPStatusError):
        # Only retry on 5xx server errors
        # Don't retry on 401 Unauthorized or 400 Bad Request
        return 500 <= exc.response.status_code < 600

    return False


def get_retry_decorator() -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    AI API 클라이언트용 재시도 데코레이터 생성(Create retry decorator for AI API clients).

    Configuration:
    - Max attempts: 3 (original attempt + 2 retries)
    - Backoff: Exponential (1s, 2s, 4s)
    - Retry on: transient network errors and 5xx server errors
    - Don't retry on: client errors (401, 400)

    Returns:
        Retry decorator function
    """
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception(_is_retryable_exception),
        reraise=True,
    )


def get_retry_strategy() -> dict[str, Any]:
    """
    AsyncRetrying용 재시도 전략 설정 반환(Return retry strategy configuration for AsyncRetrying).
    
    Returns:
        Dictionary of arguments for AsyncRetrying
    """
    return {
        "stop": stop_after_attempt(3),
        "wait": wait_exponential(multiplier=1, min=1, max=4),
        "retry": retry_if_exception(_is_retryable_exception),
        "reraise": True,
    }
