"""Utilities for parsing Perplexity responses for scoring data."""
from __future__ import annotations

import json
from typing import Optional, Tuple


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
