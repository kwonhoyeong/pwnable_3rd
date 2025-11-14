"""Redis 캐시 유틸리티(Redis cache utilities)."""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
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


class AsyncCache:
    """Redis 기반 비동기 캐시(Async redis-backed cache helper)."""

    def __init__(self, namespace: str = "pipeline", ttl_seconds: Optional[int] = None) -> None:
        env_ttl = os.getenv("CACHE_TTL_SECONDS")
        resolved_ttl: Optional[int]
        try:
            resolved_ttl = int(env_ttl) if env_ttl else None
        except ValueError:  # pragma: no cover - invalid user input
            logger.warning("Invalid CACHE_TTL_SECONDS value: %s", env_ttl)
            resolved_ttl = None

        self._ttl_seconds = ttl_seconds if ttl_seconds is not None else resolved_ttl
        self._namespace = namespace

    @staticmethod
    def _serialize(value: Any) -> Any:
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    def _build_key(self, key: str) -> str:
        return f"{self._namespace}:{key}"

    async def get(self, key: str) -> Any:
        """캐시 값 조회(Get cached value if available)."""

        try:
            redis_client = await get_redis()
        except Exception as exc:  # pragma: no cover - cache backend down
            logger.warning("Redis unavailable for cache get %s", key, exc_info=exc)
            return None

        try:
            payload = await redis_client.get(self._build_key(key))
        except Exception as exc:  # pragma: no cover - redis failure
            logger.warning("Redis error during get for %s", key, exc_info=exc)
            return None

        if payload is None:
            return None

        try:
            return json.loads(payload)
        except json.JSONDecodeError:  # pragma: no cover - corrupt cache
            logger.warning("Failed to decode cache payload for %s", key)
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """캐시에 값 저장(Store value in cache)."""

        try:
            redis_client = await get_redis()
        except Exception as exc:  # pragma: no cover - cache backend down
            logger.warning("Redis unavailable for cache set %s", key, exc_info=exc)
            return

        try:
            payload = json.dumps(value, default=self._serialize)
        except TypeError:
            logger.warning("Failed to serialize cache payload for %s", key)
            return

        ttl_seconds = ttl if ttl is not None else self._ttl_seconds
        if ttl_seconds is not None and ttl_seconds <= 0:
            ttl_seconds = None
        try:
            await redis_client.set(self._build_key(key), payload, ex=ttl_seconds)
        except Exception as exc:  # pragma: no cover - redis failure
            logger.warning("Redis error during set for %s", key, exc_info=exc)

