"""Helper utilities for agent implementations."""

from typing import Any, Awaitable, Callable, Dict, Optional

from src.core.logger import get_logger

logger = get_logger(__name__)


async def safe_call(
    coro: Awaitable[Any],
    fallback: Callable[[], Any],
    step: str,
    progress_cb: Optional[Callable[[str, str], None]] = None,
) -> Any:
    """
    Execute async operation with fallback on error.

    Attempts to execute the coroutine. If any exception occurs,
    calls the fallback function and logs a warning.

    Args:
        coro: Coroutine to execute
        fallback: Callable that returns fallback value if coro fails
        step: Step name for logging
        progress_cb: Optional progress callback (called with step and error message if exception)

    Returns:
        Result from coro or fallback value on exception
    """
    try:
        return await coro
    except Exception as exc:  # pragma: no cover - defensive logging
        error_msg = f"오류 발생, 대체 경로 사용(Error occurred, using fallback): {exc}"
        if progress_cb:
            progress_cb(step, error_msg)
        logger.warning("%s 단계에서 예외 발생", step, exc_info=exc)
        return fallback()


def build_cache_key(base: str, *parts: Optional[str]) -> str:
    """
    Build cache key from base and variable parts.

    Filters out None values and joins with colons.

    Args:
        base: Base key name (e.g., "mapping", "epss")
        parts: Variable parts to append (None values filtered)

    Returns:
        Colon-separated cache key
    """
    key_parts = [base] + [p for p in parts if p is not None]
    return ":".join(key_parts)


def filter_missing_items(
    full_list: list,
    cached_results: Optional[Dict[str, Any]],
) -> list:
    """
    Find items missing from cached results.

    Useful for batch agents that want to avoid re-fetching cached items.

    Args:
        full_list: Complete list of items to check
        cached_results: Dict of already-cached results (keys are item identifiers)

    Returns:
        List of items not in cached_results
    """
    if cached_results is None:
        return full_list

    missing = []
    for item in full_list:
        if item not in cached_results:
            missing.append(item)
    return missing
