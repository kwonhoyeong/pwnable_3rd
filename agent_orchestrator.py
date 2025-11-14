"""AI 에이전트 기반 파이프라인 오케스트레이터 모듈."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

from analyzer.app.models import AnalyzerInput, AnalyzerOutput
from analyzer.app.service import AnalyzerService
from common_lib.cache import AsyncCache
from common_lib.logger import get_logger
from cvss_fetcher.app.service import CVSSService
from epss_fetcher.app.service import EPSSService
from mapping_collector.app.models import PackageInput
from mapping_collector.app.service import MappingService
from threat_agent.app.models import ThreatCase, ThreatInput, ThreatResponse
from threat_agent.app.services import ThreatAggregationService

ProgressCallback = Callable[[str, str], None]

logger = get_logger(__name__)


async def _safe_call(
    coro: Awaitable[Any],
    fallback: Callable[[], Any],
    step: str,
    progress_cb: ProgressCallback,
) -> Any:
    """에이전트 호출 안전 래퍼."""

    try:
        return await coro
    except Exception as exc:  # pragma: no cover - defensive logging
        progress_cb(step, f"오류 발생, 대체 경로 사용(Error occurred, using fallback): {exc}")
        logger.warning("%s 단계에서 예외 발생", step, exc_info=exc)
        return fallback()


def _fallback_cves(package: str) -> List[str]:
    return [f"CVE-FAKE-{package.upper()}-0001"]


def _fallback_epss(cve_id: str) -> Dict[str, Any]:
    return {"cve_id": cve_id, "epss_score": 0.5, "collected_at": datetime.utcnow()}


def _fallback_cvss(cve_id: str) -> Dict[str, Any]:
    return {"cve_id": cve_id, "cvss_score": 5.0, "vector": None, "collected_at": datetime.utcnow()}


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
            collected_at=datetime.utcnow(),
        )

        cve_ids = await self._mapping_agent(
            mapping_service, package_payload, force, progress_cb
        )
        if not cve_ids:
            cve_ids = _fallback_cves(package_payload.package)

        epss_results, cvss_results = await asyncio.gather(
            self._epss_agent(epss_service, cve_ids, package_payload, force, progress_cb),
            self._cvss_agent(cvss_service, cve_ids, package_payload, force, progress_cb),
        )

        pipeline_results: List[Dict[str, Any]] = []
        for cve_id in cve_ids:
            threat_payload = ThreatInput(
                cve_id=cve_id,
                package=package_payload.package,
                version_range=package_payload.version_range,
            )
            threat_response = await self._threat_agent(
                threat_service,
                threat_payload,
                skip_threat_agent,
                force,
                progress_cb,
            )

            analysis_output = await self._analysis_agent(
                analyzer_service,
                threat_payload,
                epss_results[cve_id],
                cvss_results[cve_id],
                threat_response,
                force,
                progress_cb,
            )

            serialized_cases: List[Dict[str, Any]] = []
            for case in threat_response.cases:
                case_payload = case.dict()
                case_payload["collected_at"] = _normalize_timestamp(
                    case_payload.get("collected_at")
                )
                serialized_cases.append(case_payload)

            pipeline_results.append(
                {
                    "package": package_payload.package,
                    "version_range": package_payload.version_range,
                    "cve_id": cve_id,
                    "epss": {
                        "epss_score": float(epss_results[cve_id].get("epss_score", 0.0)),
                        "collected_at": _normalize_timestamp(
                            epss_results[cve_id].get("collected_at")
                        ),
                    },
                    "cvss": {
                        "cvss_score": float(cvss_results[cve_id].get("cvss_score", 0.0)),
                        "vector": cvss_results[cve_id].get("vector"),
                        "collected_at": _normalize_timestamp(
                            cvss_results[cve_id].get("collected_at")
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

        return {
            "package": package_payload.package,
            "version_range": package_payload.version_range,
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
        cache_key = f"mapping:{package_payload.package}:{package_payload.version_range}"
        cached: Optional[List[str]] = None
        if not force:
            cached = await self._cache.get(cache_key)
            if cached:
                progress_cb("MAPPING", "캐시 적중, CVE 목록 재사용(Cache hit for CVEs)")
                return cached

        progress_cb("MAPPING", f"{package_payload.package} 패키지의 CVE 조회(Fetching CVEs)")
        cve_ids = await _safe_call(
            mapping_service.fetch_cves(
                package_payload.package, package_payload.version_range
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
        cache_key = f"epss:{package_payload.package}:{package_payload.version_range}"
        if not force:
            cached = await self._cache.get(cache_key)
            if cached:
                progress_cb("EPSS", "캐시 적중, EPSS 데이터 재사용(Cache hit for EPSS)")
                return cached

        epss_results: Dict[str, Dict[str, Any]] = {}
        for cve_id in cve_ids:
            progress_cb("EPSS", f"{cve_id} 점수 조회 중(Fetching score)")
            epss_results[cve_id] = await _safe_call(
                epss_service.fetch_score(cve_id),
                fallback=lambda cid=cve_id: _fallback_epss(cid),
                step="EPSS",
                progress_cb=progress_cb,
            )

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
        cache_key = f"cvss:{package_payload.package}:{package_payload.version_range}"
        if not force:
            cached = await self._cache.get(cache_key)
            if cached:
                progress_cb("CVSS", "캐시 적중, CVSS 데이터 재사용(Cache hit for CVSS)")
                return cached

        cvss_results: Dict[str, Dict[str, Any]] = {}
        for cve_id in cve_ids:
            progress_cb("CVSS", f"{cve_id} CVSS 조회 중(Fetching CVSS score)")
            cvss_results[cve_id] = await _safe_call(
                cvss_service.fetch_score(cve_id),
                fallback=lambda cid=cve_id: _fallback_cvss(cid),
                step="CVSS",
                progress_cb=progress_cb,
            )

        await self._cache.set(cache_key, cvss_results)
        return cvss_results

    async def _threat_agent(
        self,
        threat_service: ThreatAggregationService,
        threat_payload: ThreatInput,
        skip_threat_agent: bool,
        force: bool,
        progress_cb: ProgressCallback,
    ) -> ThreatResponse:
        cache_key = (
            f"threat:{threat_payload.package}:{threat_payload.version_range}:{threat_payload.cve_id}"
        )

        if skip_threat_agent:
            progress_cb(
                "THREAT", f"{threat_payload.cve_id} 위협 수집 건너뛰기(Skipping threat collection)"
            )
            return _fallback_cases(threat_payload)

        if not force:
            cached = await self._cache.get(cache_key)
            if cached:
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
    ) -> AnalyzerOutput:
        cache_key = (
            f"analysis:{threat_payload.package}:{threat_payload.version_range}:{threat_payload.cve_id}"
        )

        if not force:
            cached = await self._cache.get(cache_key)
            if cached:
                progress_cb("ANALYZE", "캐시 적중, 분석 결과 재사용(Cache hit for analysis)")
                return AnalyzerOutput(**cached)

        analysis_input = AnalyzerInput(
            cve_id=threat_payload.cve_id,
            epss_score=float(epss_record.get("epss_score", 0.0)),
            cvss_score=float(cvss_record.get("cvss_score", 0.0)),
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

