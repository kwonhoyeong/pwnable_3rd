"""인메모리 캐시 유틸리티(In-memory cache utilities)."""
from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

try:
    from cachetools import TTLCache
except ImportError:  # pragma: no cover - optional dependency fallback
    TTLCache = None  # type: ignore[assignment]

from .config import get_settings
from .logger import get_logger

logger = get_logger(__name__)
_cache: Optional[TTLCache] = None
_lock = asyncio.Lock()


class MemoryCache:
    """메모리 기반 캐시 래퍼(Memory-based cache wrapper)."""

    def __init__(self, ttl: int = 3600, maxsize: int = 1000):
        if TTLCache is None:
            raise RuntimeError("cachetools 라이브러리가 설치되어 있지 않습니다(cachetools not installed)")
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[str]:
        """캐시에서 값 조회(Get value from cache)."""
        async with self._lock:
            return self._cache.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        """캐시에 값 저장(Set value in cache)."""
        async with self._lock:
            self._cache[key] = value

    async def delete(self, key: str) -> None:
        """캐시에서 값 삭제(Delete value from cache)."""
        async with self._lock:
            self._cache.pop(key, None)

    async def close(self) -> None:
        """캐시 종료(Close cache)."""
        async with self._lock:
            self._cache.clear()


async def get_cache() -> MemoryCache:
    """메모리 캐시 반환(Return memory cache)."""

    global _cache
    if _cache is None:
        async with _lock:
            if _cache is None:
                settings = get_settings()
                logger.info("Initializing in-memory cache")
                _cache = MemoryCache(ttl=settings.cache_ttl, maxsize=1000)
    return _cache


async def close_cache() -> None:
    """캐시 종료(Close cache)."""

    global _cache
    if _cache is not None:
        await _cache.close()
        _cache = None

