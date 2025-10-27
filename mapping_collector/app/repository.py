"""데이터 저장소 로직(Data repository logic)."""
from __future__ import annotations

from typing import List

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common_lib.logger import get_logger

logger = get_logger(__name__)


class MappingRepository:
    """패키지-CVE 매핑 저장소(Package-CVE mapping repository)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_mapping(self, package: str, version_range: str, cve_ids: List[str]) -> None:
        """매핑 정보를 저장/업데이트(Save or update mapping data)."""

        query = text(
            """
            INSERT INTO package_cve_mapping (package, version_range, cve_ids)
            VALUES (:package, :version_range, :cve_ids)
            ON CONFLICT (package, version_range)
            DO UPDATE SET cve_ids = EXCLUDED.cve_ids, updated_at = NOW()
            """
        )
        await self._session.execute(query, {"package": package, "version_range": version_range, "cve_ids": cve_ids})

    async def list_pending_packages(self) -> List[str]:
        """수집 대기 패키지 목록(Look up pending packages)."""

        query = text("SELECT package FROM package_scan_queue WHERE processed = false")
        result = await self._session.execute(query)
        return [row[0] for row in result.fetchall()]

