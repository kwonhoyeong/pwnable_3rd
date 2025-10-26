"""Redis 캐시 유틸리티(Redis cache utilities)."""
from __future__ import annotations

import asyncio
from typing import Any, Optional

import aioredis

from .config import get_settings
from .logger import get_logger

logger = get_logger(__name__)
_redis_pool: Optional[aioredis.Redis] = None
_lock = asyncio.Lock()


async def get_redis() -> aioredis.Redis:
    """Redis 연결 풀 반환(Return redis connection pool)."""

    global _redis_pool
    if _redis_pool is None:
        async with _lock:
            if _redis_pool is None:
                settings = get_settings()
                logger.info("Connecting to Redis")
                _redis_pool = await aioredis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    return _redis_pool


async def close_redis() -> None:
    """Redis 연결 종료(Close redis connection)."""

    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.close()
        _redis_pool = None

