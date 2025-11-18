"""AI 에이전트 기반 파이프라인 오케스트레이터 모듈."""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

from analyzer.app.models import AnalyzerInput, AnalyzerOutput
from analyzer.app.repository import AnalysisRepository
from analyzer.app.service import AnalyzerService
from common_lib.cache import AsyncCache
from common_lib.db import get_session
from common_lib.logger import get_logger
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

from src.core.fallback import FallbackProvider
from src.core.utils.timestamps import normalize_timestamp, ensure_datetime
from src.core.persistence import PersistenceManager
from src.core.serialization import serialize_threat_case, serialize_pipeline_result
from src.core.agent_helpers import safe_call, build_cache_key, filter_missing_items

ProgressCallback = Callable[[str, str], None]

logger = get_logger(__name__)

# Use FallbackProvider for consistent fallback data generation
_fallback_provider = FallbackProvider()


def _resolve_epss_entry(results: Dict[str, Dict[str, Any]], cve_id: str) -> Dict[str, Any]:
    entry = results.get(cve_id)
    if entry is None:
        logger.warning("Missing EPSS result for %s, using fallback defaults", cve_id)
        entry = _fallback_provider.fallback_epss(cve_id)
        results[cve_id] = entry
    return entry


def _resolve_cvss_entry(results: Dict[str, Dict[str, Any]], cve_id: str) -> Dict[str, Any]:
    entry = results.get(cve_id)
    if entry is None:
        logger.warning("Missing CVSS result for %s, using fallback defaults", cve_id)
        entry = _fallback_provider.fallback_cvss(cve_id)
        results[cve_id] = entry
    return entry


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

        pipeline_results: List[Dict[str, Any]] = []
        async with get_session() as session:
            # Initialize PersistenceManager for database operations
            persistence_manager = PersistenceManager(session)

            cve_ids = await self._mapping_agent(
                mapping_service, package_payload, force, progress_cb
            )
            if not cve_ids:
                cve_ids = _fallback_provider.fallback_cves(package_payload.package)

            # Persist mappings if session is available
            await persistence_manager.persist_mappings(
                package_payload.package, package_payload.version_range, cve_ids
            )

            epss_results, cvss_results = await asyncio.gather(
                self._epss_agent(epss_service, cve_ids, package_payload, force, progress_cb),
                self._cvss_agent(cvss_service, cve_ids, package_payload, force, progress_cb),
            )

            # Persist EPSS and CVSS scores if session is available
            await persistence_manager.persist_epss_scores(epss_results)
            await persistence_manager.persist_cvss_scores(cvss_results)

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
                )

                # Persist threat cases if session is available
                serialized_cases_db = [serialize_threat_case(case) for case in threat_response.cases]
                await persistence_manager.persist_threat_cases(
                    threat_payload.cve_id,
                    threat_payload.package,
                    threat_payload.version_range,
                    serialized_cases_db,
                )

                analysis_output = await self._analysis_agent(
                    analyzer_service,
                    threat_payload,
                    epss_record,
                    cvss_record,
                    threat_response,
                    force,
                    progress_cb,
                )

                # Persist analysis if session is available
                await persistence_manager.persist_analysis(
                    cve_id=analysis_output.cve_id,
                    risk_level=analysis_output.risk_level,
                    recommendations=analysis_output.recommendations,
                    analysis_summary=analysis_output.analysis_summary,
                    generated_at=analysis_output.generated_at,
                )

                # Serialize complete pipeline result
                result = serialize_pipeline_result(
                    package=package_payload.package,
                    version_range=package_payload.version_range,
                    cve_id=cve_id,
                    epss_record=epss_record,
                    cvss_record=cvss_record,
                    threat_response=threat_response,
                    analysis_output=analysis_output,
                )
                pipeline_results.append(result)

        logger.info(
            "Pipeline completed (package=%s, version=%s, results=%d)",
            package_payload.package,
            package_payload.version_range,
            len(pipeline_results),
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
            if cached is not None:
                progress_cb("MAPPING", "캐시 적중, CVE 목록 재사용(Cache hit for CVEs)")
                return cached

        progress_cb("MAPPING", f"{package_payload.package} 패키지의 CVE 조회(Fetching CVEs)")
        cve_ids = await safe_call(
            mapping_service.fetch_cves(
                package_payload.package, package_payload.version_range
            ),
            fallback=lambda: _fallback_provider.fallback_cves(package_payload.package),
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
        cache_key = f"epss:{package_payload.package}:{package_payload.version_range}"
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
            epss_results[cve_id] = await safe_call(
                epss_service.fetch_score(cve_id),
                fallback=lambda cid=cve_id: _fallback_provider.fallback_epss(cid),
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
        cache_key = f"cvss:{package_payload.package}:{package_payload.version_range}"
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
            cvss_results[cve_id] = await safe_call(
                cvss_service.fetch_score(cve_id),
                fallback=lambda cid=cve_id: _fallback_provider.fallback_cvss(cid),
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
    ) -> ThreatResponse:
        cache_key = (
            f"threat:{threat_payload.package}:{threat_payload.version_range}:{threat_payload.cve_id}"
        )

        if skip_threat_agent:
            progress_cb(
                "THREAT", f"{threat_payload.cve_id} 위협 수집 건너뛰기(Skipping threat collection)"
            )
            return _fallback_provider.fallback_threat_cases(threat_payload)

        if not force:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                progress_cb("THREAT", "캐시 적중, 위협 사례 재사용(Cache hit for threat cases)")
                return ThreatResponse(**cached)

        progress_cb("THREAT", f"{threat_payload.cve_id} 공격 사례 수집 중(Collecting threat cases)")
        threat_response = await safe_call(
            threat_service.collect(threat_payload),
            fallback=lambda payload=threat_payload: _fallback_provider.fallback_threat_cases(payload),
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
            if cached is not None:
                progress_cb("ANALYZE", "캐시 적중, 분석 결과 재사용(Cache hit for analysis)")
                return AnalyzerOutput(**cached)

        # Convert EPSS and CVSS scores, handling None values
        epss_val = epss_record.get("epss_score")
        cvss_val = cvss_record.get("cvss_score")

        analysis_input = AnalyzerInput(
            cve_id=threat_payload.cve_id,
            epss_score=float(epss_val) if epss_val is not None else None,
            cvss_score=float(cvss_val) if cvss_val is not None else None,
            cases=[case.dict() for case in threat_response.cases],
            package=threat_payload.package,
            version_range=threat_payload.version_range,
        )

        progress_cb("ANALYZE", f"{threat_payload.cve_id} 위험도 평가 중(Analyzing risk)")
        analysis_output = await safe_call(
            analyzer_service.analyze(analysis_input),
            fallback=lambda payload=analysis_input: _fallback_provider.fallback_analysis(payload),
            step="ANALYZE",
            progress_cb=progress_cb,
        )

        await self._cache.set(cache_key, analysis_output.dict())
        return analysis_output
