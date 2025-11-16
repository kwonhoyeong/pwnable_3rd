"""ThreatAgent 데이터 저장소(ThreatAgent data repository)."""
from __future__ import annotations

import json
from typing import Any, List

from pydantic.json import pydantic_encoder
from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from common_lib.logger import get_logger

logger = get_logger(__name__)


def _serialize_case_for_jsonb(case: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a threat case dict to a JSON-serializable format for JSONB storage.

    Uses Pydantic's encoder to recursively handle all Pydantic types including:
    - HttpUrl objects -> str
    - datetime objects -> ISO-8601 string
    - Nested structures with Pydantic types
    - Other special types (UUID, Decimal, etc.)
    """
    # Use Pydantic's encoder and parse back to ensure full JSON compatibility
    # This handles all Pydantic types recursively and robustly
    return json.loads(json.dumps(case, default=pydantic_encoder))


class ThreatRepository:
    """위협 사례 저장 레이어(Storage layer for threat cases)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_cases(
        self, cve_id: str, package: str, version_range: str, cases: List[dict[str, object]]
    ) -> None:
        """사례 정보를 저장/갱신(Store or update collected cases)."""

        # Serialize cases to JSON-safe format for JSONB storage
        # This handles HttpUrl -> str and datetime -> ISO-8601 conversion
        serialized_cases = [_serialize_case_for_jsonb(case) for case in cases]

        # Explicitly bind 'cases' parameter as JSONB to ensure asyncpg handles it correctly
        # Without this, SQLAlchemy treats it as TEXT and asyncpg fails with 'list has no encode'
        query = text(
            """
            INSERT INTO threat_cases (cve_id, package, version_range, cases)
            VALUES (:cve_id, :package, :version_range, :cases)
            ON CONFLICT (cve_id, package, version_range)
            DO UPDATE SET cases = EXCLUDED.cases, updated_at = NOW()
            """
        ).bindparams(bindparam("cases", type_=JSONB))

        await self._session.execute(
            query,
            {
                "cve_id": cve_id,
                "package": package,
                "version_range": version_range,
                "cases": serialized_cases,
            },
        )

    async def is_duplicate(self, cve_id: str, source: str) -> bool:
        """중복 여부 검사(Check duplication)."""

        query = text(
            """
            SELECT 1 FROM threat_cases, jsonb_array_elements(threat_cases.cases) AS case
            WHERE threat_cases.cve_id = :cve_id AND case->>'source' = :source LIMIT 1
            """
        )
        result = await self._session.execute(query, {"cve_id": cve_id, "source": source})
        return result.first() is not None

