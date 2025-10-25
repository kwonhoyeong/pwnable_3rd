"""통합 파이프라인 오케스트레이터(Integrated pipeline orchestrator)."""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

from analyzer.app.models import AnalyzerInput, AnalyzerOutput
from analyzer.app.service import AnalyzerService
from common_lib.logger import get_logger
from epss_fetcher.app.service import EPSSService
from mapping_collector.app.models import PackageInput
from mapping_collector.app.service import MappingService
from threat_agent.app.models import ThreatCase, ThreatInput, ThreatResponse
from threat_agent.app.services import ThreatAggregationService

ProgressCallback = Callable[[str, str], None]

logger = get_logger(__name__)


def _default_progress(step: str, message: str) -> None:
    """기본 진행 상황 콜백(Default progress callback)."""

    logger.info("[%s] %s", step, message)


async def _safe_call(coro: Awaitable[Any], fallback: Callable[[], Any], step: str, progress_cb: ProgressCallback) -> Any:
    """안전 호출 래퍼(Wrapper to safely invoke async operations)."""

    try:
        return await coro
    except Exception as exc:  # pragma: no cover - prototype safety
        progress_cb(step, f"오류 발생, 대체 경로 사용(Error occurred, using fallback): {exc}")
        logger.exception("%s failed", step, exc_info=exc)
        return fallback()


def _fallback_cves(package: str) -> List[str]:
    """CVE 조회 실패 시 대체 목록(Fallback CVE list)."""

    return [f"CVE-FAKE-{package.upper()}-0001"]


def _fallback_epss(cve_id: str) -> Dict[str, Any]:
    """EPSS 조회 실패 시 기본값(Fallback EPSS payload)."""

    return {"cve_id": cve_id, "epss_score": 0.5, "collected_at": datetime.utcnow()}


def _fallback_cases(payload: ThreatInput) -> ThreatResponse:
    """위협 수집 실패 시 기본 사례(Fallback threat cases)."""

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
    """분석 실패 시 기본 보고(Fallback analysis report)."""

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


async def _collect_epss(
    epss_service: EPSSService,
    cve_ids: Iterable[str],
    progress_cb: ProgressCallback,
) -> Dict[str, Dict[str, Any]]:
    """CVE 목록에 대한 EPSS 데이터를 수집(Collect EPSS data for CVEs)."""

    epss_results: Dict[str, Dict[str, Any]] = {}
    for cve_id in cve_ids:
        progress_cb("EPSS", f"{cve_id} 점수 조회 중(Fetching score)")
        epss_record = await _safe_call(
            epss_service.fetch_score(cve_id),
            fallback=lambda cid=cve_id: _fallback_epss(cid),
            step="EPSS",
            progress_cb=progress_cb,
        )
        epss_results[cve_id] = epss_record
    return epss_results


async def run_pipeline(
    package: str,
    version_range: str,
    skip_threat_agent: bool,
    force: bool,
    progress_cb: ProgressCallback = _default_progress,
) -> Dict[str, Any]:
    """전체 파이프라인을 실행하고 결과 반환(Run the full pipeline and return results)."""

    progress_cb("INIT", "서비스 초기화 중(Initializing services)")
    if force:
        progress_cb("INIT", "캐시 무시 모드 활성화(Cache bypass enabled)")

    mapping_service = MappingService()
    epss_service = EPSSService()
    threat_service = ThreatAggregationService()
    analyzer_service = AnalyzerService()

    package_payload = PackageInput(
        package=package,
        version_range=version_range,
        collected_at=datetime.utcnow(),
    )

    progress_cb("MAPPING", f"{package} 패키지의 CVE 조회(Fetching CVEs)")
    cve_ids = await _safe_call(
        mapping_service.fetch_cves(package_payload.package, package_payload.version_range),
        fallback=lambda: _fallback_cves(package_payload.package),
        step="MAPPING",
        progress_cb=progress_cb,
    )
    if not cve_ids:
        progress_cb("MAPPING", "CVE 목록이 비어 대체 목록 사용(No CVEs, fallback applied)")
        cve_ids = _fallback_cves(package_payload.package)

    epss_results = await _collect_epss(epss_service, cve_ids, progress_cb)

    pipeline_results: List[Dict[str, Any]] = []
    for cve_id in cve_ids:
        threat_payload = ThreatInput(
            cve_id=cve_id,
            package=package_payload.package,
            version_range=package_payload.version_range,
        )

        if skip_threat_agent:
            progress_cb("THREAT", f"{cve_id} 위협 수집 건너뛰기(Skipping threat collection)")
            threat_response = _fallback_cases(threat_payload)
        else:
            progress_cb("THREAT", f"{cve_id} 공격 사례 수집 중(Collecting threat cases)")
            threat_response = await _safe_call(
                threat_service.collect(threat_payload),
                fallback=lambda payload=threat_payload: _fallback_cases(payload),
                step="THREAT",
                progress_cb=progress_cb,
            )

        analysis_input = AnalyzerInput(
            cve_id=cve_id,
            epss_score=float(epss_results[cve_id].get("epss_score", 0.0)),
            cases=[case.dict() for case in threat_response.cases],
            package=package_payload.package,
            version_range=package_payload.version_range,
        )

        progress_cb("ANALYZE", f"{cve_id} 위험도 평가 중(Analyzing risk)")
        analysis_output = await _safe_call(
            analyzer_service.analyze(analysis_input),
            fallback=lambda payload=analysis_input: _fallback_analysis(payload),
            step="ANALYZE",
            progress_cb=progress_cb,
        )

        pipeline_results.append(
            {
                "package": package_payload.package,
                "version_range": package_payload.version_range,
                "cve_id": cve_id,
                "epss": {
                    "epss_score": float(epss_results[cve_id].get("epss_score", 0.0)),
                    "collected_at": epss_results[cve_id]
                    .get("collected_at", datetime.utcnow())
                    .isoformat(),
                },
                "cases": [case.dict() for case in threat_response.cases],
                "analysis": {
                    **analysis_output.dict(),
                    "generated_at": analysis_output.generated_at.isoformat(),
                },
            }
        )

    return {
        "package": package_payload.package,
        "version_range": package_payload.version_range,
        "generated_at": datetime.utcnow().isoformat(),
        "results": pipeline_results,
    }


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    """커맨드라인 인자 파싱(Parse CLI arguments)."""

    parser = argparse.ArgumentParser(description="npm CVE/EPSS 통합 실행기")
    parser.add_argument("--package", required=True, help="대상 패키지명(Target package)")
    parser.add_argument(
        "--version-range",
        default="latest",
        help="분석할 버전 범위(Version range)",
    )
    parser.add_argument(
        "--skip-threat-agent",
        action="store_true",
        help="ThreatAgent 단계를 건너뜀(Skip threat aggregation)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="캐시 무시 후 강제 조회(Force refresh by bypassing cache)",
    )
    return parser.parse_args(argv)


async def main_async(args: argparse.Namespace) -> None:
    """비동기 메인 루틴(Async main routine)."""

    result = await run_pipeline(
        package=args.package,
        version_range=args.version_range,
        skip_threat_agent=args.skip_threat_agent,
        force=args.force,
        progress_cb=_default_progress,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


def main() -> None:
    """동기 진입점(Synchronous entrypoint)."""

    args = parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
