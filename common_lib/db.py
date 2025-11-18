"""데이터베이스 연결 풀(Database connection pool)."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy import text
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
        if not settings.enable_database:
            logger.info("Database access disabled via configuration; running in in-memory mode")
            return None
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
        settings = get_settings()
        if not settings.enable_database:
            logger.info("Database disabled; yielding in-memory session")
            yield None
            return

        if _session_factory is None:
            engine = await get_engine()
            if engine is None:
                logger.warning("Database not available, continuing without DB persistence")
                yield None
                return
            _session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        session = _session_factory()
        if not await _ensure_connection(session):
            await _safe_close(session)
            session = None
            yield None
            return

        yield session
    except Exception as exc:  # pragma: no cover - skeleton
        if session is not None:
            try:
                await session.rollback()
            except Exception:
                pass

        # Only suppress DB connection/authentication errors for CLI testing
        # Re-raise other errors so business logic bugs are not hidden
        import asyncpg
        from sqlalchemy.exc import OperationalError, DBAPIError

        if isinstance(exc, (asyncpg.exceptions.PostgresError, OperationalError, DBAPIError)):
            logger.warning("Database connection error, continuing without DB: %s", exc)
            # Allow pipeline to continue without DB for testing
        else:
            # Re-raise business logic errors
            logger.error("Session error (not a DB connection issue): %s", exc)
            raise
    finally:
        if session is not None:
            await _safe_close(session)


async def _ensure_connection(session: AsyncSession) -> bool:
    """Ensure database connectivity; disable persistence if unreachable."""

    try:
        await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=3.0)
        return True
    except asyncio.TimeoutError:
        logger.info("Database connectivity check timed out; running without DB persistence.")
        return False
    except Exception as exc:
        logger.info("Database connectivity check failed; running without DB persistence: %s", exc)
        return False


async def _safe_close(session: AsyncSession) -> None:
    """Close session with timeout to avoid hanging on network issues."""

    try:
        logger.info("Closing database session.")
        await asyncio.wait_for(session.close(), timeout=1.0)
    except asyncio.TimeoutError:
        logger.info("Database session close timed out; ignoring.")
    except Exception:
        pass


async def get_session_dependency() -> AsyncIterator[AsyncSession | None]:
    """
    Wrapper for frameworks (e.g., FastAPI) that expect dependency callables instead of context managers.

    Usage:
        session: AsyncSession | None = Depends(get_session_dependency)
    """

    async with get_session() as session:
        yield session
