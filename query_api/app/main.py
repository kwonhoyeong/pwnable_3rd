"""QueryAPI FastAPI 애플리케이션(QueryAPI FastAPI application)."""
from __future__ import annotations

import traceback
import uuid
from typing import Any

from fastapi import Depends, FastAPI, Query, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from common_lib.db import get_session
from common_lib.errors import AppException, ExternalServiceError
from common_lib.logger import get_logger
from common_lib.observability import request_id_ctx

from .models import QueryResponse
from .repository import QueryRepository
from .service import QueryService

logger = get_logger(__name__)
app = FastAPI(title="QueryAPI")
service = QueryService()


# Middleware for request ID tracking
class RequestIDMiddleware(BaseHTTPMiddleware):
    """요청 ID 추적 미들웨어(Middleware for request ID tracking and correlation)."""

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        """
        각 요청에 대해 요청 ID를 생성하고 설정(Generate and set request ID for each request).

        Args:
            request: FastAPI request object
            call_next: Next middleware/handler

        Returns:
            Response with X-Request-ID header
        """
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Set request ID in context for logging
        token = request_id_ctx.set(request_id)

        try:
            # Process the request
            response = await call_next(request)
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            # Reset context
            request_id_ctx.reset(token)


# Add middleware to app
app.add_middleware(RequestIDMiddleware)


# Global Exception Handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle application exceptions with standardized error format."""
    logger.warning(
        "AppException: %s (code=%s)",
        exc.message,
        exc.error_code,
        extra={"details": exc.details},
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unexpected errors."""
    logger.error(
        "Unexpected error: %s",
        str(exc),
        exc_info=exc,
        extra={"path": request.url.path, "method": request.method},
    )

    # Log full traceback for debugging
    error_traceback = traceback.format_exc()
    logger.debug("Error traceback: %s", error_traceback)

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Unexpected server error",
            }
        },
    )


@app.get("/api/v1/query", response_model=QueryResponse, tags=["query"])
async def query(
    package: str | None = Query(default=None),
    cve_id: str | None = Query(default=None),
    session=Depends(get_session),
) -> QueryResponse:
    """패키지 또는 CVE 기반 조회 실행(Execute query by package or CVE)."""

    if session is None:
        raise ExternalServiceError(
            service_name="Database",
            reason="Database connection unavailable",
        )

    repository = QueryRepository(session)
    # Exceptions will be handled by global exception handlers
    response = await service.query(repository, package, cve_id)
    return response


@app.get("/api/v1/history", tags=["history"])
async def get_history(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to fetch"),
    session=Depends(get_session),
) -> dict[str, object]:
    """분석 히스토리 조회(Fetch analysis history with pagination)."""

    if session is None:
        raise ExternalServiceError(
            service_name="Database",
            reason="Database connection unavailable",
        )

    repository = QueryRepository(session)
    # Exceptions will be handled by global exception handlers
    history = await repository.get_history(skip=skip, limit=limit)
    return {
        "skip": skip,
        "limit": limit,
        "total_returned": len(history),
        "records": history,
    }


@app.get("/api/v1/stats", tags=["stats"])
async def get_stats(session=Depends(get_session)) -> dict[str, object]:
    """위험도 통계 조회(Get risk distribution statistics)."""

    if session is None:
        raise ExternalServiceError(
            service_name="Database",
            reason="Database connection unavailable",
        )

    repository = QueryRepository(session)
    # Exceptions will be handled by global exception handlers
    risk_stats = await repository.get_risk_stats()
    total_scans = sum(risk_stats.values())
    return {
        "total_scans": total_scans,
        "risk_distribution": risk_stats,
    }


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """헬스체크 엔드포인트(Health check endpoint)."""

    return {"status": "ok"}

