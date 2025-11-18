"""Pipeline result serialization utilities."""

from typing import Any, Dict

from analyzer.app.models import AnalyzerOutput
from threat_agent.app.models import ThreatResponse

from src.core.utils.timestamps import normalize_timestamp
from src.core.data.threat_case import serialize_threat_case


def serialize_pipeline_result(
    package: str,
    version_range: str,
    cve_id: str,
    epss_record: Dict[str, Any],
    cvss_record: Dict[str, Any],
    threat_response: ThreatResponse,
    analysis_output: AnalyzerOutput,
) -> Dict[str, Any]:
    """
    Serialize a complete pipeline result for a single CVE.

    Combines EPSS, CVSS, threat cases, and analysis into a single JSON-serializable dict.

    Args:
        package: Package name
        version_range: Version range (e.g., 'latest')
        cve_id: CVE identifier
        epss_record: EPSS data dict (with epss_score and collected_at)
        cvss_record: CVSS data dict (with cvss_score, vector, collected_at)
        threat_response: ThreatResponse with threat cases
        analysis_output: AnalyzerOutput with risk analysis

    Returns:
        Serialized pipeline result ready for JSON output
    """
    # Serialize threat cases
    serialized_cases = [serialize_threat_case(case) for case in threat_response.cases]

    # Handle None values for EPSS and CVSS scores
    epss_val = epss_record.get("epss_score")
    cvss_val = cvss_record.get("cvss_score")

    return {
        "package": package,
        "version_range": version_range,
        "cve_id": cve_id,
        "epss": {
            "epss_score": float(epss_val) if epss_val is not None else None,
            "collected_at": normalize_timestamp(epss_record.get("collected_at")),
        },
        "cvss": {
            "cvss_score": float(cvss_val) if cvss_val is not None else None,
            "vector": cvss_record.get("vector"),
            "collected_at": normalize_timestamp(cvss_record.get("collected_at")),
        },
        "cases": serialized_cases,
        "analysis": {
            **analysis_output.dict(),
            "generated_at": normalize_timestamp(analysis_output.generated_at),
        },
    }
