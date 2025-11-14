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

    async def list_pending_packages(self) -> List[dict[str, object]]:
        """수집 대기 패키지 목록(Look up pending packages)."""

        query = text(
            """
            SELECT id, package, version_range
            FROM package_scan_queue
            WHERE processed = false
            ORDER BY created_at ASC
            FOR UPDATE SKIP LOCKED
            """
        )
        result = await self._session.execute(query)
        rows = result.fetchall()
        return [
            {"id": row.id, "package": row.package, "version_range": row.version_range}
            for row in rows
        ]

    async def mark_processed(self, queue_id: int) -> None:
        """큐 항목 처리 완료 표시(Mark queue entry as processed)."""

        query = text("UPDATE package_scan_queue SET processed = true WHERE id = :queue_id")
        await self._session.execute(query, {"queue_id": queue_id})
