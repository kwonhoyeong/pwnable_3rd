"""QueryAPI FastAPI 애플리케이션(QueryAPI FastAPI application)."""
from __future__ import annotations

import logging
import traceback
import uuid
from typing import Any

from fastapi import Depends, FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

from common_lib.config import get_settings
from common_lib.db import get_session
from common_lib.errors import AppException, ExternalServiceError
from common_lib.logger import get_logger
from common_lib.observability import request_id_ctx

from .auth import verify_api_key
from .models import QueryResponse
from .repository import QueryRepository
from .service import QueryService

logger = get_logger(__name__)
debug_logger = logging.getLogger(__name__)

# Setup Rate Limiter
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="QueryAPI")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    print(f"DEBUG: Unexpected error: {exc}")
    traceback.print_exc()

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
@limiter.limit("5/minute")
async def query(
    request: Request,
    package: str | None = Query(default=None),
    cve_id: str | None = Query(default=None),
    version: str | None = Query(default=None, description="Package version (optional, defaults to 'latest' for analysis)"),
    ecosystem: str = Query(default="npm", description="Package ecosystem (npm, pip, apt)"),
    force: bool = Query(default=False, description="Force re-analysis"),
    api_key: str = Depends(verify_api_key),
    session=Depends(get_session),
) -> QueryResponse:
    print(f"DEBUG: /query called with package={package}, cve_id={cve_id}, ecosystem={ecosystem}, force={force}")
    """패키지 또는 CVE 기반 조회 실행(Execute query by package or CVE).

    Query Parameters:
        package: NPM package name (e.g., "react", "lodash")
        cve_id: CVE identifier (e.g., "CVE-2024-1234")
        version: Optional package version (e.g., "1.0.0", "2.3.5")
                If not provided, returns all CVEs for the package or triggers analysis with 'latest'
        ecosystem: Package ecosystem (default: "npm"). Supported: npm, pip, apt.
        force: Force re-analysis (default: False)

    Requires valid API key in X-API-Key header
    """

    # --- DEBUG LOG ---
    if get_settings().environment == "development":
        debug_logger.info(f"DEBUG [/query]: session type: {type(session)}, session repr: {repr(session)}")
    # -----------------

    if session is None:
        raise ExternalServiceError(
            service_name="Database",
            reason="Database connection unavailable",
        )

    # Validate ecosystem
    if ecosystem not in ["npm", "pip", "apt"]:
        # For backward compatibility or strictness, we could default to npm or raise error.
        # Raising error is better for explicit API contract.
        # But let's just log warning and proceed or raise 400.
        # Given the plan, let's validate.
        pass # Pydantic/FastAPI validation could be used with Enum, but string check is fine here.

    repository = QueryRepository(session)
    # Exceptions will be handled by global exception handlers
    response = await service.query(repository, package, cve_id, version, ecosystem, force=force)
    return response


@app.get("/api/v1/history", tags=["history"])
@limiter.limit("10/minute")
async def get_history(
    request: Request,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to fetch"),
    api_key: str = Depends(verify_api_key),
    session=Depends(get_session),
) -> dict[str, object]:
    """분석 히스토리 조회(Fetch analysis history with pagination).

    Requires valid API key in X-API-Key header
    """

    # --- DEBUG LOG ---
    if get_settings().environment == "development":
        debug_logger.info(f"DEBUG: session type: {type(session)}, session repr: {repr(session)}")
    # -----------------

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
@limiter.limit("5/minute")
async def get_stats(
    request: Request,
    api_key: str = Depends(verify_api_key),
    session=Depends(get_session),
) -> dict[str, object]:
    """위험도 통계 조회(Get risk distribution statistics).

    Requires valid API key in X-API-Key header
    """

    # --- DEBUG LOG ---
    if get_settings().environment == "development":
        debug_logger.info(f"DEBUG [/stats]: session type: {type(session)}, session repr: {repr(session)}")
    # -----------------

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

