"""데이터베이스 연결 풀(Database connection pool)."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from .config import get_settings
from .logger import get_logger

logger = get_logger(__name__)
_engine: AsyncEngine | None = None
_session_factory: sessionmaker | None = None


async def get_engine() -> AsyncEngine | None:
    """비동기 엔진 제공(Provide async engine). Returns None if DB is unavailable."""

    global _engine
    if _engine is None:
        settings = get_settings()
        logger.info("Initializing async engine")
        try:
            _engine = create_async_engine(settings.postgres_dsn, future=True, echo=False)
        except Exception as exc:
            logger.warning("Failed to create database engine, continuing without DB: %s", exc)
            return None
    return _engine


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession | None]:
    """세션 컨텍스트 관리자(Session context manager). Returns None if DB is unavailable."""

    global _session_factory
    engine = None
    session = None

    try:
        if _session_factory is None:
            engine = await get_engine()
            if engine is None:
                logger.warning("Database not available, continuing without DB persistence")
                yield None
                return
            _session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        session = _session_factory()
        yield session
    except Exception as exc:  # pragma: no cover - skeleton
        if session is not None:
            try:
                await session.rollback()
            except Exception:
                pass
        logger.warning("Database session error, continuing without DB: %s", exc)
        # Don't raise - allow pipeline to continue without DB
    finally:
        if session is not None:
            try:
                await session.close()
            except Exception:
                pass

