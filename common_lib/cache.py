"""Redis 캐시 유틸리티(Redis cache utilities)."""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any, Optional, cast

try:
    import redis.asyncio as redis
except ImportError:  # pragma: no cover - optional dependency fallback
    redis = None  # type: ignore[assignment]

if TYPE_CHECKING:  # pragma: no cover - typing only
    from redis.asyncio import Redis
else:
    Redis = Any

from .config import get_settings
from .logger import get_logger

logger = get_logger(__name__)
_redis_pool: Optional[Redis] = None
_lock = asyncio.Lock()


async def get_redis() -> Redis:
    """Redis 연결 풀 반환(Return redis connection pool)."""

    global _redis_pool
    if redis is None:
        raise RuntimeError("redis 라이브러리가 설치되어 있지 않습니다(Redis client not installed)")
    if _redis_pool is None:
        async with _lock:
            if _redis_pool is None:
                settings = get_settings()
                logger.info("Connecting to Redis")
                _redis_pool = await redis.from_url(  # type: ignore[assignment]
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
    return cast(Redis, _redis_pool)


async def close_redis() -> None:
    """Redis 연결 종료(Close redis connection)."""

    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.close()
        _redis_pool = None

