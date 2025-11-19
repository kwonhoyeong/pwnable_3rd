"""Utilities for parsing Perplexity responses for scoring data."""
from __future__ import annotations

import json
from typing import List, Optional, Tuple


def _load_json_blob(raw_text: str) -> Optional[dict]:
    """Best effort JSON parsing helper."""

    if not raw_text:
        return None
    try:
        return json.loads(raw_text.strip())
    except json.JSONDecodeError:
        return None


def parse_epss_response(raw_text: str) -> Tuple[Optional[float], Optional[str]]:
    """Extract EPSS score information from Perplexity output."""

    data = _load_json_blob(raw_text)
    if data is None:
        return None, None

    score = data.get("epss_score")
    source = data.get("source")

    if score is None:
        return None, source

    try:
        score_value = float(score)
    except (TypeError, ValueError):
        return None, source

    if 0.0 <= score_value <= 1.0:
        return score_value, source

    return None, source


def parse_cvss_response(raw_text: str) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    """Extract CVSS score, vector, and source from Perplexity output."""

    data = _load_json_blob(raw_text)
    if data is None:
        return None, None, None

    score = data.get("cvss_score")
    vector = data.get("vector")
    source = data.get("source")

    if score is None:
        return None, vector, source

    try:
        score_value = float(score)
    except (TypeError, ValueError):
        return None, vector, source

    if 0.0 <= score_value <= 10.0:
        return score_value, vector, source

    return None, vector, source


def normalize_cve_ids(cve_ids: List[str]) -> List[str]:
    """Normalize a list of CVE identifiers to uppercase and deduplicate."""

    normalized: List[str] = []
    seen: set[str] = set()
    for entry in cve_ids:
        if not isinstance(entry, str):
            continue
        candidate = entry.strip().upper()
        if not candidate.startswith("CVE-"):
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)

    return normalized


def parse_cve_mapping_response(raw_text: str) -> Tuple[List[str], Optional[str]]:
    """Extract a list of CVE identifiers and optional source from Perplexity output."""

    data = _load_json_blob(raw_text)
    if data is None:
        return [], None

    raw_ids = data.get("cve_ids")
    if not isinstance(raw_ids, list):
        return [], data.get("source")

    normalized = normalize_cve_ids(raw_ids)
    return normalized, data.get("source")
