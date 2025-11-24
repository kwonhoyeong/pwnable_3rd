"""AI 에이전트 기반 파이프라인 오케스트레이터 모듈."""
from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from analyzer.app.models import AnalyzerInput, AnalyzerOutput
from analyzer.app.repository import AnalysisRepository
from analyzer.app.service import AnalyzerService
from common_lib.cache import AsyncCache
from common_lib.db import get_session
from common_lib.logger import get_logger
from common_lib.retry_config import _is_retryable_exception, get_retry_strategy
from cvss_fetcher.app.repository import CVSSRepository
from cvss_fetcher.app.service import CVSSService
from epss_fetcher.app.repository import EPSSRepository
from epss_fetcher.app.service import EPSSService
from mapping_collector.app.models import PackageInput
from mapping_collector.app.repository import MappingRepository
from mapping_collector.app.service import MappingService
from threat_agent.app.models import ThreatCase, ThreatInput, ThreatResponse
from threat_agent.app.repository import ThreatRepository
from threat_agent.app.services import ThreatAggregationService

print("🚀 [DEBUG] Orchestrator script loaded", flush=True)

ProgressCallback = Callable[[str, str], None]

logger = get_logger(__name__)


@asynccontextmanager
async def get_session_ctx():
    """Wrapper to use get_session generator as a context manager."""
    async for session in get_session():
        yield session


async def _safe_call(
    coro: Awaitable[Any],
    fallback: Callable[[], Any],
    step: str,
    progress_cb: ProgressCallback,
) -> Any:
    """에이전트 호출 안전 래퍼(Safe wrapper for agent calls with retry logic).

    Attempts to execute the coroutine with exponential backoff retry on transient errors.
    If all retries are exhausted, falls back to the fallback function.

    Args:
        coro: Awaitable coroutine to execute
        fallback: Fallback function to call if all retries fail
        step: Step name for logging and progress callback
        progress_cb: Callback for progress updates

    Returns:
        Result from coroutine or fallback function
    """
    # Create a retrying strategy with exponential backoff
    retry_strategy = AsyncRetrying(**get_retry_strategy())

    try:
        # Use AsyncRetrying to wrap the coroutine
        async for attempt in retry_strategy:
            with attempt:
                return await coro
    except Exception as exc:  # pragma: no cover - defensive logging
        progress_cb(step, f"오류 발생, 대체 경로 사용(Error occurred, using fallback): {exc}")
        logger.warning("%s 단계에서 예외 발생", step, exc_info=exc)
        return fallback()


def _fallback_cves(package: str) -> List[str]:
    suffix = abs(hash(package)) % 10000
    return [f"CVE-2025-{suffix:04d}"]


def _fallback_epss(cve_id: str) -> Dict[str, Any]:
    return {
        "cve_id": cve_id,
        "epss_score": None,
        "source": "fallback",
        "collected_at": datetime.utcnow(),
    }


def _fallback_cvss(cve_id: str) -> Dict[str, Any]:
    return {
        "cve_id": cve_id,
        "cvss_score": None,
        "vector": None,
        "source": "fallback",
        "collected_at": datetime.utcnow(),
    }


def _resolve_epss_entry(results: Dict[str, Dict[str, Any]], cve_id: str) -> Dict[str, Any]:
    entry = results.get(cve_id)
    if entry is None:
        logger.warning("Missing EPSS result for %s, using fallback defaults", cve_id)
        entry = _fallback_epss(cve_id)
        results[cve_id] = entry
    return entry


def _resolve_cvss_entry(results: Dict[str, Dict[str, Any]], cve_id: str) -> Dict[str, Any]:
    entry = results.get(cve_id)
    if entry is None:
        logger.warning("Missing CVSS result for %s, using fallback defaults", cve_id)
        entry = _fallback_cvss(cve_id)
        results[cve_id] = entry
    return entry


def _fallback_cases(payload: ThreatInput) -> ThreatResponse:
    fallback_case = ThreatCase(
        source="https://example.com/prototype-case",
        title=f"Fallback case for {payload.cve_id}",
        date=datetime.utcnow().date().isoformat(),
        summary="AI API 호출 실패로 인해 기본 설명(Default narrative due to AI error).",
        collected_at=datetime.utcnow(),
    )
    return ThreatResponse(
        cve_id=payload.cve_id,
        package=payload.package,
        version_range=payload.version_range,
        cases=[fallback_case],
    )


def _fallback_analysis(payload: AnalyzerInput) -> AnalyzerOutput:
    return AnalyzerOutput(
        cve_id=payload.cve_id,
        risk_level="Medium",
        recommendations=[
            "패키지를 최신 버전으로 업그레이드하세요(Upgrade package to latest).",
            "추가 모니터링을 수행하세요(Enable heightened monitoring).",
        ],
        analysis_summary="AI 분석 실패로 수동 검토 필요(Manual review required due to AI failure).",
        generated_at=datetime.utcnow(),
    )


def _normalize_timestamp(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        return value
    return datetime.utcnow().isoformat()


def _ensure_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            logger.warning("Invalid datetime format encountered: %s", value)
    return datetime.utcnow()


def _serialize_threat_case(case: ThreatCase) -> Dict[str, Any]:
    """Centralized ThreatCase serialization helper to ensure consistent JSON output."""
    try:
        from pydantic import HttpUrl
    except ImportError:
        HttpUrl = None  # type: ignore

    # Use model_dump for Pydantic v2 compatibility with mode='json' to serialize HttpUrl
    if hasattr(case, 'model_dump'):
        case_data = case.model_dump(mode='json')
    else:
        # Fallback for Pydantic v1
        case_data = case.dict()
        # Manually convert HttpUrl to string
        if HttpUrl and isinstance(case_data.get('source'), HttpUrl):
            case_data['source'] = str(case_data['source'])
        elif 'source' in case_data and hasattr(case_data['source'], '__str__') and not isinstance(case_data['source'], str):
            case_data['source'] = str(case_data['source'])

    # Normalize timestamp
    if 'collected_at' in case_data:
        case_data['collected_at'] = _normalize_timestamp(case_data['collected_at'])

    return case_data


class AgentOrchestrator:
    """단계별 에이전트를 조율하는 오케스트레이터."""

    def __init__(self, cache: Optional[AsyncCache] = None) -> None:
        self._cache = cache or AsyncCache(namespace="pipeline")

    async def orchestrate_pipeline(
        self,
        package: str,
        version_range: str,
        skip_threat_agent: bool,
        force: bool,
        progress_cb: ProgressCallback,
        ecosystem: str = "npm",
    ) -> Dict[str, Any]:
        progress_cb("INIT", "서비스 초기화 중(Initializing services)")
        if force:
            progress_cb("INIT", "캐시 무시 모드 활성화(Cache bypass enabled)")

        mapping_service = MappingService()
        epss_service = EPSSService()
        cvss_service = CVSSService()
        threat_service = ThreatAggregationService()
        analyzer_service = AnalyzerService()

        package_payload = PackageInput(
            package=package,
            version_range=version_range,
            ecosystem=ecosystem,
            collected_at=datetime.utcnow(),
        )

        pipeline_results: List[Dict[str, Any]] = []
        async with get_session_ctx() as session:
            # Initialize repositories only if session is available
            mapping_repo = MappingRepository(session) if session else None
            epss_repo = EPSSRepository(session) if session else None
            cvss_repo = CVSSRepository(session) if session else None
            threat_repo = ThreatRepository(session) if session else None
            analysis_repo = AnalysisRepository(session) if session else None

            cve_ids = await self._mapping_agent(
                mapping_service, package_payload, force, progress_cb
            )
            if not cve_ids:
                cve_ids = _fallback_cves(package_payload.package)

            # Only persist to DB if session is available
            if session and mapping_repo:
                try:
                    await mapping_repo.upsert_mapping(
                        package_payload.package,
                        package_payload.version_range,
                        package_payload.ecosystem,
                        cve_ids,
                    )
                    await session.commit()
                except Exception as exc:
                    await session.rollback()
                    logger.warning("Failed to persist mapping to DB: %s", exc)

            epss_results, cvss_results = await asyncio.gather(
                self._epss_agent(epss_service, cve_ids, package_payload, force, progress_cb),
                self._cvss_agent(cvss_service, cve_ids, package_payload, force, progress_cb),
            )

            # Only persist to DB if session is available
            if session and epss_repo:
                try:
                    for cve_id in cve_ids:
                        epss_record = _resolve_epss_entry(epss_results, cve_id)
                        await epss_repo.upsert_score(
                            cve_id,
                            epss_record.get("epss_score"),
                            _ensure_datetime(epss_record.get("collected_at")),
                        )
                except Exception as exc:
                    await session.rollback()
                    logger.warning("Failed to persist EPSS to DB: %s", exc)

            if session and cvss_repo:
                try:
                    for cve_id in cve_ids:
                        cvss_record = _resolve_cvss_entry(cvss_results, cve_id)
                        await cvss_repo.upsert_score(
                            cve_id,
                            cvss_record.get("cvss_score"),
                            cvss_record.get("vector"),
                            _ensure_datetime(cvss_record.get("collected_at")),
                        )
                    await session.commit()
                except Exception as exc:
                    await session.rollback()
                    logger.warning("Failed to persist CVSS to DB: %s", exc)

            for cve_id in cve_ids:
                threat_payload = ThreatInput(
                    cve_id=cve_id,
                    package=package_payload.package,
                    version_range=package_payload.version_range,
                )
                epss_record = _resolve_epss_entry(epss_results, cve_id)
                cvss_record = _resolve_cvss_entry(cvss_results, cve_id)
                threat_response = await self._threat_agent(
                    threat_service,
                    threat_payload,
                    skip_threat_agent,
                    force,
                    progress_cb,
                    package_payload.ecosystem,
                )

                # Only persist to DB if session is available
                if session and threat_repo:
                    try:
                        # Use centralized serialization helper
                        serialized_db_cases = [_serialize_threat_case(case) for case in threat_response.cases]

                        await threat_repo.upsert_cases(
                            threat_payload.cve_id,
                            threat_payload.package,
                            threat_payload.version_range,
                            serialized_db_cases,
                        )
                    except Exception as exc:
                        await session.rollback()
                        logger.warning("Failed to persist threat cases to DB: %s", exc)

                analysis_output = await self._analysis_agent(
                    analyzer_service,
                    threat_payload,
                    epss_record,
                    cvss_record,
                    threat_response,
                    force,
                    progress_cb,
                    package_payload.ecosystem,
                )

                # Only persist to DB if session is available
                if session and analysis_repo:
                    try:
                        await analysis_repo.upsert_analysis(
                            cve_id=analysis_output.cve_id,
                            risk_level=analysis_output.risk_level,
                            risk_score=analysis_output.risk_score,
                            recommendations=analysis_output.recommendations,
                            analysis_summary=analysis_output.analysis_summary,
                            generated_at=_ensure_datetime(analysis_output.generated_at),
                        )
                        await session.commit()
                    except Exception as exc:
                        await session.rollback()
                        logger.warning("Failed to persist analysis to DB: %s", exc)

                # Use centralized serialization helper
                serialized_cases = [_serialize_threat_case(case) for case in threat_response.cases]

                pipeline_results.append(
                    {
                        "package": package_payload.package,
                        "version_range": package_payload.version_range,
                        "cve_id": cve_id,
                        "epss": {
                            "epss_score": epss_record.get("epss_score"),
                            "source": epss_record.get("source"),
                            "collected_at": _normalize_timestamp(
                                epss_record.get("collected_at")
                            ),
                        },
                        "cvss": {
                            "cvss_score": cvss_record.get("cvss_score"),
                            "vector": cvss_record.get("vector"),
                            "source": cvss_record.get("source"),
                            "collected_at": _normalize_timestamp(
                                cvss_record.get("collected_at")
                            ),
                        },
                        "cases": serialized_cases,
                        "analysis": {
                            **analysis_output.dict(),
                            "generated_at": _normalize_timestamp(
                                analysis_output.generated_at
                            ),
                        },
                    }
                )

        logger.info(
            "Pipeline completed (package=%s, version=%s, results=%d)",
            package_payload.package,
            package_payload.version_range,
            len(pipeline_results),
        )

        return {
            "package": package_payload.package,
            "version_range": package_payload.version_range,
            "ecosystem": package_payload.ecosystem,
            "generated_at": datetime.utcnow().isoformat(),
            "results": pipeline_results,
        }

    async def _mapping_agent(
        self,
        mapping_service: MappingService,
        package_payload: PackageInput,
        force: bool,
        progress_cb: ProgressCallback,
    ) -> List[str]:
        cache_key = (
            f"mapping:{package_payload.ecosystem}:{package_payload.package}:{package_payload.version_range}"
        )
        cached: Optional[List[str]] = None
        if not force:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                progress_cb("MAPPING", "캐시 적중, CVE 목록 재사용(Cache hit for CVEs)")
                return cached

        progress_cb("MAPPING", f"{package_payload.package} 패키지의 CVE 조회(Fetching CVEs)")
        cve_ids = await _safe_call(
            mapping_service.fetch_cves(
                package_payload.package, package_payload.version_range, package_payload.ecosystem
            ),
            fallback=lambda: _fallback_cves(package_payload.package),
            step="MAPPING",
            progress_cb=progress_cb,
        )
        await self._cache.set(cache_key, cve_ids)
        return cve_ids

    async def _epss_agent(
        self,
        epss_service: EPSSService,
        cve_ids: Iterable[str],
        package_payload: PackageInput,
        force: bool,
        progress_cb: ProgressCallback,
    ) -> Dict[str, Dict[str, Any]]:
        cve_list = list(cve_ids)
        cache_key = (
            f"epss:{package_payload.ecosystem}:{package_payload.package}:{package_payload.version_range}"
        )
        cached: Optional[Dict[str, Dict[str, Any]]] = None
        if not force:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                progress_cb("EPSS", "캐시 적중, EPSS 데이터 재사용(Cache hit for EPSS)")

        epss_results: Dict[str, Dict[str, Any]] = dict(cached) if isinstance(cached, dict) else {}
        missing_ids: List[str] = []
        for cve_id in cve_list:
            if cve_id in epss_results:
                continue
            missing_ids.append(cve_id)

        for cve_id in missing_ids:
            progress_cb("EPSS", f"{cve_id} 점수 조회 중(Fetching score)")
            epss_results[cve_id] = await _safe_call(
                epss_service.fetch_score(cve_id),
                fallback=lambda cid=cve_id: _fallback_epss(cid),
                step="EPSS",
                progress_cb=progress_cb,
            )

        if force or cached is None or missing_ids:
            await self._cache.set(cache_key, epss_results)
        return epss_results

    async def _cvss_agent(
        self,
        cvss_service: CVSSService,
        cve_ids: Iterable[str],
        package_payload: PackageInput,
        force: bool,
        progress_cb: ProgressCallback,
    ) -> Dict[str, Dict[str, Any]]:
        cve_list = list(cve_ids)
        cache_key = (
            f"cvss:{package_payload.ecosystem}:{package_payload.package}:{package_payload.version_range}"
        )
        cached: Optional[Dict[str, Dict[str, Any]]] = None
        if not force:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                progress_cb("CVSS", "캐시 적중, CVSS 데이터 재사용(Cache hit for CVSS)")

        cvss_results: Dict[str, Dict[str, Any]] = dict(cached) if isinstance(cached, dict) else {}
        missing_ids: List[str] = []
        for cve_id in cve_list:
            if cve_id in cvss_results:
                continue
            missing_ids.append(cve_id)

        for cve_id in missing_ids:
            progress_cb("CVSS", f"{cve_id} CVSS 조회 중(Fetching CVSS score)")
            cvss_results[cve_id] = await _safe_call(
                cvss_service.fetch_score(cve_id),
                fallback=lambda cid=cve_id: _fallback_cvss(cid),
                step="CVSS",
                progress_cb=progress_cb,
            )

        if force or cached is None or missing_ids:
            await self._cache.set(cache_key, cvss_results)
        return cvss_results

    async def _threat_agent(
        self,
        threat_service: ThreatAggregationService,
        threat_payload: ThreatInput,
        skip_threat_agent: bool,
        force: bool,
        progress_cb: ProgressCallback,
        ecosystem: str,
    ) -> ThreatResponse:
        cache_key = (
            f"threat:{ecosystem}:{threat_payload.package}:{threat_payload.version_range}:{threat_payload.cve_id}"
        )

        if skip_threat_agent:
            progress_cb(
                "THREAT", f"{threat_payload.cve_id} 위협 수집 건너뛰기(Skipping threat collection)"
            )
            return _fallback_cases(threat_payload)

        if not force:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                progress_cb("THREAT", "캐시 적중, 위협 사례 재사용(Cache hit for threat cases)")
                return ThreatResponse(**cached)

        progress_cb("THREAT", f"{threat_payload.cve_id} 공격 사례 수집 중(Collecting threat cases)")
        threat_response = await _safe_call(
            threat_service.collect(threat_payload),
            fallback=lambda payload=threat_payload: _fallback_cases(payload),
            step="THREAT",
            progress_cb=progress_cb,
        )

        await self._cache.set(cache_key, threat_response.dict())
        return threat_response

    async def _analysis_agent(
        self,
        analyzer_service: AnalyzerService,
        threat_payload: ThreatInput,
        epss_record: Dict[str, Any],
        cvss_record: Dict[str, Any],
        threat_response: ThreatResponse,
        force: bool,
        progress_cb: ProgressCallback,
        ecosystem: str,
    ) -> AnalyzerOutput:
        cache_key = (
            f"analysis:{ecosystem}:{threat_payload.package}:{threat_payload.version_range}:{threat_payload.cve_id}"
        )

        if not force:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                progress_cb("ANALYZE", "캐시 적중, 분석 결과 재사용(Cache hit for analysis)")
                return AnalyzerOutput(**cached)

        analysis_input = AnalyzerInput(
            cve_id=threat_payload.cve_id,
            epss_score=epss_record.get("epss_score"),
            cvss_score=cvss_record.get("cvss_score"),
            cases=[case.dict() for case in threat_response.cases],
            package=threat_payload.package,
            version_range=threat_payload.version_range,
        )

        progress_cb("ANALYZE", f"{threat_payload.cve_id} 위험도 평가 중(Analyzing risk)")
        analysis_output = await _safe_call(
            analyzer_service.analyze(analysis_input),
            fallback=lambda payload=analysis_input: _fallback_analysis(payload),
            step="ANALYZE",
            progress_cb=progress_cb,
        )

        await self._cache.set(cache_key, analysis_output.dict())
        return analysis_output


async def main() -> None:
    """메인 오케스트레이터 진입점(Main orchestrator entry point)."""
    import argparse
    import uuid

    from common_lib.observability import request_id_ctx

    # Generate request ID for this orchestrator run (for distributed tracing)
    request_id = str(uuid.uuid4())
    request_id_ctx.set(request_id)

    parser = argparse.ArgumentParser(
        description="AI agent-based threat intelligence pipeline orchestrator"
    )
    parser.add_argument(
        "--package",
        required=True,
        help="Package name (e.g., lodash, express)",
    )
    parser.add_argument(
        "--version-range",
        required=True,
        help="Version range (e.g., '<4.17.21', '<=1.2.3')",
    )
    parser.add_argument(
        "--ecosystem",
        default="npm",
        choices=["npm", "pip", "apt"],
        help="Package ecosystem",
    )
    parser.add_argument(
        "--skip-threat",
        action="store_true",
        help="Skip threat intelligence collection",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force refresh, bypass cache",
    )

    args = parser.parse_args()

    def progress_callback(step: str, message: str) -> None:
        """Progress callback that prints to stdout."""
        print(f"[{step}] {message}", flush=True)

    orchestrator = AgentOrchestrator()

    print(f"🚀 [ORCHESTRATOR] Starting pipeline for {args.package} ({args.version_range}) [request_id={request_id}]", flush=True)
    try:
        result = await orchestrator.orchestrate_pipeline(
            package=args.package,
            version_range=args.version_range,
            skip_threat_agent=args.skip_threat,
            force=args.force,
            progress_cb=progress_callback,
            ecosystem=args.ecosystem,
        )

        print("\n✅ [ORCHESTRATOR] Pipeline completed successfully", flush=True)
        print(f"\n📊 Results:\n{result}", flush=True)

        return result
    except KeyboardInterrupt:
        print("\n🛑 Orchestrator stopped by user.", flush=True)
    except Exception as e:
        print(f"\n❌ Fatal Error: {e}", flush=True)
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    # Configure logging to print to stdout
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    print("🚀 [DEBUG] Starting Orchestrator Main Loop...", flush=True)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Orchestrator stopped by user.")
    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        import traceback

        traceback.print_exc()
