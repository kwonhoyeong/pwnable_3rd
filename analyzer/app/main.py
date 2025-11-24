"""Analyzer FastAPI 애플리케이션 모듈(Analyzer FastAPI application module)."""
from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException

from common_lib.db import get_session
from common_lib.logger import get_logger

from .models import AnalyzerInput, AnalyzerOutput
from .repository import AnalysisRepository
from .service import AnalyzerService

logger = get_logger(__name__)
app = FastAPI(title="Analyzer")
service = AnalyzerService()


@app.post("/api/v1/analyze", response_model=AnalyzerOutput, tags=["analysis"])
async def analyze(data: AnalyzerInput, session=Depends(get_session)) -> AnalyzerOutput:
    """위험 분석 실행 및 저장(Execute risk analysis and persist result)."""

    try:
        result = await service.analyze(data)
    except Exception as exc:  # pragma: no cover - skeleton
        logger.exception("Analysis failed", exc_info=exc)
        raise HTTPException(status_code=500, detail="Failed to analyze threat") from exc

    repository = AnalysisRepository(session)
    await repository.upsert_analysis(
        result.cve_id,
        result.risk_level,
        result.recommendations,
        result.analysis_summary,
        result.generated_at,
        result.risk_score,
    )
    await session.commit()
    return result


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """헬스체크 엔드포인트(Health check endpoint)."""

    return {"status": "ok"}

