"""Redis 클라이언트 및 작업 제출 함수(Redis client and job submission functions)."""
from __future__ import annotations

import json
from typing import Optional

import redis.asyncio as redis

from common_lib.config import get_settings
from common_lib.logger import get_logger

logger = get_logger(__name__)
_redis_client: redis.Redis | None = None

# Redis configuration
ANALYSIS_QUEUE_KEY = "analysis_tasks"
REDIS_TIMEOUT = 5.0  # seconds


async def get_redis_client() -> redis.Redis | None:
    """비동기 Redis 클라이언트 제공(Provide async Redis client).

    Returns:
        Redis client or None if connection fails
    """
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    try:
        settings = get_settings()
        redis_url = settings.redis_url

        if not redis_url:
            logger.warning("Redis URL not configured; skipping Redis client initialization")
            return None

        logger.info("Initializing async Redis client")
        _redis_client = redis.from_url(redis_url, decode_responses=True)

        # Test connection
        await _redis_client.ping()
        logger.info("Redis client connected successfully")
        return _redis_client

    except Exception as exc:
        logger.warning("Failed to initialize Redis client: %s", exc, exc_info=exc)
        return None


async def close_redis_client() -> None:
    """Redis 클라이언트 연결 종료(Close Redis client connection)."""
    global _redis_client

    if _redis_client is not None:
        try:
            await _redis_client.close()
            logger.info("Redis client closed")
            _redis_client = None
        except Exception as exc:
            logger.warning("Error closing Redis client: %s", exc, exc_info=exc)


async def submit_analysis_job(
    package_name: str,
    version: str | None = None,
    force: bool = False,
    source: str = "web_query",
) -> bool:
    """분석 작업을 Redis 큐에 제출(Submit analysis job to Redis queue).

    Args:
        package_name: NPM package name to analyze
        version: Package version (default: "latest" if None)
        force: Force re-analysis even if already cached
        source: Source identifier for the job request

    Returns:
        True if job was submitted successfully, False otherwise
    """
    try:
        client = await get_redis_client()

        if client is None:
            logger.warning("Redis client unavailable; cannot submit analysis job for %s", package_name)
            return False

        # Prepare job payload
        job_payload = {
            "package": package_name,
            "version": version or "latest",
            "force": force,
            "source": source,
        }

        # Serialize to JSON
        job_json = json.dumps(job_payload)

        # Push to Redis list (right push - append to end)
        result = await client.rpush(ANALYSIS_QUEUE_KEY, job_json)

        if result:
            logger.info(
                "Analysis job submitted to queue for %s@%s (force=%s, source=%s)",
                package_name,
                job_payload["version"],
                force,
                source,
            )
            return True
        else:
            logger.error("Failed to push job to Redis queue for %s", package_name)
            return False

    except Exception as exc:
        logger.error(
            "Error submitting analysis job to Redis for %s: %s",
            package_name,
            exc,
            exc_info=exc,
        )
        return False


async def get_pending_analysis_count() -> int:
    """대기 중인 분석 작업 수 조회(Get count of pending analysis jobs).

    Returns:
        Number of pending jobs in the queue
    """
    try:
        client = await get_redis_client()

        if client is None:
            return 0

        count = await client.llen(ANALYSIS_QUEUE_KEY)
        return count or 0

    except Exception as exc:
        logger.warning("Error getting analysis queue length: %s", exc)
        return 0
