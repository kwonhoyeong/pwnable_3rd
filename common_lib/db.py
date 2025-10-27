"""데이터베이스 연결 풀(Database connection pool)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from .config import get_settings
from .logger import get_logger

logger = get_logger(__name__)
_engine: AsyncEngine | None = None
_session_factory: sessionmaker | None = None


async def get_engine() -> AsyncEngine:
    """비동기 엔진 제공(Provide async engine)."""

    global _engine
    if _engine is None:
        settings = get_settings()
        logger.info("Initializing async engine")

        # SQLite 데이터 디렉토리 생성
        db_url = settings.database_url
        if db_url.startswith("sqlite"):
            # sqlite+aiosqlite:///./data/threatdb.sqlite -> ./data/threatdb.sqlite
            db_path = db_url.split("///", 1)[1] if "///" in db_url else "data/threatdb.sqlite"
            db_dir = Path(db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"SQLite database directory: {db_dir}")

        _engine = create_async_engine(settings.database_url, future=True, echo=False)
    return _engine


async def get_session() -> AsyncIterator[AsyncSession]:
    """세션 컨텍스트 관리자(Session context manager)."""

    global _session_factory
    if _session_factory is None:
        engine = await get_engine()
        _session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with _session_factory() as session:
        try:
            yield session
        except Exception as exc:  # pragma: no cover - skeleton
            logger.exception("Database session error", exc_info=exc)
            raise

