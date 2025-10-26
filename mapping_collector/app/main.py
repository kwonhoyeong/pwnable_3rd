"""MappingCollector 애플리케이션 엔트리포인트(Application entrypoint)."""
from __future__ import annotations

import asyncio

from fastapi import FastAPI

from common_lib.logger import get_logger

from .scheduler import MappingScheduler

logger = get_logger(__name__)
app = FastAPI(title="MappingCollector")
scheduler = MappingScheduler()


@app.on_event("startup")
async def startup_event() -> None:
    """서비스 시작 시 스케줄러 초기화(Initialize scheduler on startup)."""

    asyncio.create_task(scheduler.start())
    logger.info("MappingCollector scheduler started")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """서비스 종료 시 스케줄러 중지(Stop scheduler on shutdown)."""

    await scheduler.stop()
    logger.info("MappingCollector scheduler stopped")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """헬스체크 엔드포인트(Health check endpoint)."""

    return {"status": "ok"}

