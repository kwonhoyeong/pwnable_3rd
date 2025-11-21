"""스케줄러 로직(Scheduler logic)."""
from __future__ import annotations

import asyncio
from datetime import datetime

from common_lib.db import get_session
from common_lib.logger import get_logger

from .models import PackageMapping
from .repository import MappingRepository
from .service import MappingService

logger = get_logger(__name__)


class MappingScheduler:
    """주기적 작업 실행기(Periodic job runner)."""

    def __init__(self, interval_seconds: int = 300) -> None:
        self._interval_seconds = interval_seconds
        self._service = MappingService()
        self._is_running = False

    async def start(self) -> None:
        """스케줄러 시작(Start scheduler loop)."""

        if self._is_running:
            return
        self._is_running = True
        while self._is_running:
            await self._run_once()
            await asyncio.sleep(self._interval_seconds)

    async def stop(self) -> None:
        """스케줄러 중지(Stop scheduler loop)."""

        self._is_running = False

    async def _run_once(self) -> None:
        """단일 실행(Tick execution)."""

        async for session in get_session():
            if session is None:
                logger.warning("Database session unavailable; skipping scheduler tick.")
                return

            repository = MappingRepository(session)
            try:
                pending_jobs = await repository.list_pending_packages()
                for job in pending_jobs:
                    package_name = str(job["package"])
                    version_range = str(job["version_range"])
                    ecosystem = str(job.get("ecosystem") or "npm")
                    cve_ids = await self._service.fetch_cves(package_name, version_range, ecosystem)
                    source = "aggregated"  # Default source for scheduler-collected mappings
                    mapping = PackageMapping(
                        package=package_name,
                        version_range=version_range,
                        ecosystem=ecosystem,
                        cve_ids=cve_ids,
                        collected_at=datetime.utcnow(),
                        source=source,
                    )
                    await repository.upsert_mapping(
                        mapping.package, mapping.version_range, mapping.ecosystem, mapping.cve_ids
                    )
                    await repository.mark_processed(int(job["id"]))
                await session.commit()
                logger.info("MappingScheduler tick processed %d jobs.", len(pending_jobs))
            except Exception:
                await session.rollback()
                logger.exception("MappingScheduler tick failed; transaction rolled back.")
                raise
            finally:
                break
