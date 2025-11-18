"""QueryAPI FastAPI 애플리케이션(QueryAPI FastAPI application)."""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException, Query

from common_lib.db import get_session_dependency
from common_lib.logger import get_logger

from .models import QueryResponse
from .repository import QueryRepository
from .service import QueryService

logger = get_logger(__name__)
app = FastAPI(title="QueryAPI")
service = QueryService()


@app.get("/api/v1/query", response_model=QueryResponse, tags=["query"])
async def query(
    package: str | None = Query(default=None),
    cve_id: str | None = Query(default=None),
    session=Depends(get_session_dependency),
) -> QueryResponse:
    """패키지 또는 CVE 기반 조회 실행(Execute query by package or CVE)."""

    if session is None:
        raise HTTPException(status_code=503, detail="Database session is unavailable")

    repository = QueryRepository(session)
    try:
        response = await service.query(repository, package, cve_id)
    except ValueError as exc:
        logger.warning("Invalid query parameters", exc_info=exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return response


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """헬스체크 엔드포인트(Health check endpoint)."""

    return {"status": "ok"}
