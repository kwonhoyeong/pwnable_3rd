"""EPSSFetcher FastAPI 애플리케이션(FastAPI application for EPSSFetcher)."""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from common_lib.db import get_session_dependency
from common_lib.logger import get_logger

from .models import EPSSInput, EPSSRecord
from .repository import EPSSRepository
from .service import EPSSService

logger = get_logger(__name__)
app = FastAPI(title="EPSSFetcher")
service = EPSSService()


@app.post("/api/v1/epss", response_model=EPSSRecord, tags=["epss"])
async def fetch_epss(data: EPSSInput, session=Depends(get_session_dependency)) -> EPSSRecord:
    """EPSS 점수를 조회하고 저장(Retrieve and persist EPSS score)."""

    if session is None:
        raise HTTPException(status_code=503, detail="Database session is unavailable")

    try:
        result = await service.fetch_score(data.cve_id)
    except Exception as exc:  # pragma: no cover - skeleton
        logger.exception("Failed to fetch EPSS", exc_info=exc)
        raise HTTPException(status_code=502, detail="Failed to fetch EPSS data") from exc

    repository = EPSSRepository(session)
    await repository.upsert_score(result["cve_id"], result["epss_score"], result["collected_at"])
    await session.commit()
    return EPSSRecord(**result)


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """헬스체크 엔드포인트(Health check endpoint)."""

    return {"status": "ok"}
