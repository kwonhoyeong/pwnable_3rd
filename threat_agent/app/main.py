"""ThreatAgent FastAPI 애플리케이션(ThreatAgent FastAPI application)."""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from common_lib.db import get_session
from common_lib.logger import get_logger

from .models import ThreatInput, ThreatResponse
from .repository import ThreatRepository
from .services import ThreatAggregationService

logger = get_logger(__name__)
app = FastAPI(title="ThreatAgent")
service = ThreatAggregationService()


@app.post("/api/v1/threats", response_model=ThreatResponse, tags=["threats"])
async def collect_threats(payload: ThreatInput, session=Depends(get_session)) -> ThreatResponse:
    """위협 정보를 수집 후 저장(Collect and persist threat intelligence)."""

    try:
        response = await service.collect(payload)
    except Exception as exc:  # pragma: no cover - skeleton
        logger.exception("Threat collection failed", exc_info=exc)
        raise HTTPException(status_code=502, detail="Threat collection failed") from exc

    repository = ThreatRepository(session)
    await repository.upsert_cases(
        response.cve_id,
        response.package,
        response.version_range,
        [case.dict() for case in response.cases],
    )
    await session.commit()
    return response


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """헬스체크 엔드포인트(Health check endpoint)."""

    return {"status": "ok"}

