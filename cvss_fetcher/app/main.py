"""CVSSFetcher FastAPI 애플리케이션(FastAPI application for CVSSFetcher)."""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from common_lib.db import get_session_dependency
from common_lib.logger import get_logger

from .models import CVSSInput, CVSSRecord
from .repository import CVSSRepository
from .service import CVSSService

logger = get_logger(__name__)
app = FastAPI(title="CVSSFetcher")
service = CVSSService()


@app.post("/api/v1/cvss", response_model=CVSSRecord, tags=["cvss"])
async def fetch_cvss(data: CVSSInput, session=Depends(get_session_dependency)) -> CVSSRecord:
    """CVSS 점수를 조회하고 저장(Retrieve and persist CVSS score)."""

    if session is None:
        raise HTTPException(status_code=503, detail="Database session is unavailable")

    try:
        result = await service.fetch_score(data.cve_id)
    except Exception as exc:  # pragma: no cover - skeleton
        logger.exception("Failed to fetch CVSS", exc_info=exc)
        raise HTTPException(status_code=502, detail="Failed to fetch CVSS data") from exc

    repository = CVSSRepository(session)
    await repository.upsert_score(
        result["cve_id"], result["cvss_score"], result.get("vector"), result["collected_at"]
    )
    await session.commit()
    return CVSSRecord(**result)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """헬스체크 엔드포인트(Health check endpoint)."""

    return {"status": "ok"}
