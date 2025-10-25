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

        async with get_session() as session:
            repository = MappingRepository(session)
            pending_packages = await repository.list_pending_packages()
            for package_name in pending_packages:
                cve_ids = await self._service.fetch_cves(package_name, "latest")
                mapping = PackageMapping(
                    package=package_name,
                    version_range="latest",
                    cve_ids=cve_ids,
                    collected_at=datetime.utcnow(),
                )
                await repository.upsert_mapping(mapping.package, mapping.version_range, mapping.cve_ids)
            await session.commit()

