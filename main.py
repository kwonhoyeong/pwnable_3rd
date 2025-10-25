"""프로토타입 실행 스크립트(Prototype runner script)."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List

from analyzer.app.models import AnalyzerInput, AnalyzerOutput
from analyzer.app.service import AnalyzerService
from common_lib.logger import get_logger
from epss_fetcher.app.service import EPSSService
from mapping_collector.app.models import PackageInput
from mapping_collector.app.service import MappingService
from threat_agent.app.models import ThreatCase, ThreatInput, ThreatResponse
from threat_agent.app.services import ThreatAggregationService

logger = get_logger(__name__)


async def _safe_fetch_cves(mapping_service: MappingService, payload: PackageInput) -> List[str]:
    """CVE 목록 안전 조회(Safely fetch CVE identifiers)."""

    try:
        cve_ids = await mapping_service.fetch_cves(payload.package, payload.version_range)
    except Exception as exc:  # pragma: no cover - prototype safeguard
        logger.warning("Mapping fetch failed, using fallback", exc_info=exc)
        cve_ids = []
    if not cve_ids:
        logger.info("No CVE IDs returned, injecting sample identifiers for demo")
        return ["CVE-2023-1234"]
    return cve_ids


async def _safe_fetch_epss(epss_service: EPSSService, cve_id: str) -> Dict[str, Any]:
    """EPSS 점수 안전 조회(Safely fetch EPSS score)."""

    try:
        record = await epss_service.fetch_score(cve_id)
    except Exception as exc:  # pragma: no cover - prototype safeguard
        logger.warning("EPSS lookup failed, using fallback", exc_info=exc)
        record = {
            "cve_id": cve_id,
            "epss_score": 0.5,
            "collected_at": datetime.utcnow(),
        }
    return record


async def _safe_collect_threats(
    threat_service: ThreatAggregationService, payload: ThreatInput
) -> ThreatResponse:
    """위협 정보 안전 수집(Safely collect threat intelligence)."""

    try:
        return await threat_service.collect(payload)
    except Exception as exc:  # pragma: no cover - prototype safeguard
        logger.warning("Threat aggregation failed, using fallback", exc_info=exc)
        fallback_case = ThreatCase(
            source="https://example.com/prototype-case",
            title=f"Prototype case for {payload.cve_id}",
            date=datetime.utcnow().date().isoformat(),
            summary=(
                "AI API 호출 실패로 인해 기본 설명(Default summary due to AI API failure)."
                " 예상 위협 시나리오를 검토하고 패치 계획을 수립하세요(Review risk scenario and plan patch)."
            ),
            collected_at=datetime.utcnow(),
        )
        return ThreatResponse(
            cve_id=payload.cve_id,
            package=payload.package,
            version_range=payload.version_range,
            cases=[fallback_case],
        )


async def _safe_analyze(analyzer_service: AnalyzerService, payload: AnalyzerInput) -> AnalyzerOutput:
    """위험 분석 안전 실행(Safely perform risk analysis)."""

    try:
        return await analyzer_service.analyze(payload)
    except Exception as exc:  # pragma: no cover - prototype safeguard
        logger.warning("Analyzer execution failed, using fallback", exc_info=exc)
        return AnalyzerOutput(
            cve_id=payload.cve_id,
            risk_level="Medium",
            recommendations=[
                "패키지를 최신 버전으로 업그레이드하세요(Upgrade to the latest package version).",
                "취약한 서비스에 대한 모니터링을 강화하세요(Strengthen monitoring for vulnerable services).",
            ],
            analysis_summary=(
                "AI API 호출 실패로 인해 기본 요약 제공(Default summary provided due to AI API error)."
                " CVE 위험도를 수동으로 검토하세요(Review CVE risk manually)."
            ),
            generated_at=datetime.utcnow(),
        )


async def run_prototype() -> None:
    """엔드투엔드 프로토타입 실행(Run end-to-end prototype)."""

    package_payload = PackageInput(
        package="lodash",
        version_range="<4.17.21",
        collected_at=datetime.utcnow(),
    )

    mapping_service = MappingService()
    epss_service = EPSSService()
    threat_service = ThreatAggregationService()
    analyzer_service = AnalyzerService()

    cve_ids = await _safe_fetch_cves(mapping_service, package_payload)

    results: List[Dict[str, Any]] = []
    for cve_id in cve_ids:
        epss_record = await _safe_fetch_epss(epss_service, cve_id)
        threat_payload = ThreatInput(
            cve_id=cve_id,
            package=package_payload.package,
            version_range=package_payload.version_range,
        )
        threat_report = await _safe_collect_threats(threat_service, threat_payload)
        analysis_input = AnalyzerInput(
            cve_id=cve_id,
            epss_score=float(epss_record.get("epss_score", 0.0)),
            cases=[case.dict() for case in threat_report.cases],
            package=package_payload.package,
            version_range=package_payload.version_range,
        )
        analysis_output = await _safe_analyze(analyzer_service, analysis_input)

        results.append(
            {
                "package": package_payload.package,
                "version_range": package_payload.version_range,
                "cve_id": cve_id,
                "epss": {
                    "epss_score": float(epss_record.get("epss_score", 0.0)),
                    "collected_at": epss_record.get("collected_at", datetime.utcnow()).isoformat(),
                },
                "cases": [case.dict() for case in threat_report.cases],
                "analysis": {
                    **analysis_output.dict(),
                    "generated_at": analysis_output.generated_at.isoformat(),
                },
            }
        )

    print(json.dumps({"results": results}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(run_prototype())
