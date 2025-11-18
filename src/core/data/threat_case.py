"""ThreatCase serialization utilities for consistent JSON output."""

from typing import Any, Dict

from threat_agent.app.models import ThreatCase

from src.core.utils.timestamps import normalize_timestamp


def serialize_threat_case(case: ThreatCase) -> Dict[str, Any]:
    """
    Serialize a ThreatCase to a JSON-compatible dictionary.

    Handles Pydantic v1/v2 compatibility and ensures consistent timestamp formatting.

    Args:
        case: ThreatCase instance to serialize

    Returns:
        Dictionary with all fields ready for JSON serialization
    """
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

    # Normalize timestamp to ISO format string
    if 'collected_at' in case_data:
        case_data['collected_at'] = normalize_timestamp(case_data['collected_at'])

    return case_data
