"""Timestamp utilities for consistent datetime handling across the pipeline."""

from datetime import datetime
from typing import Any, Union

from src.core.logger import get_logger

logger = get_logger(__name__)


def normalize_timestamp(value: Any) -> str:
    """
    Convert various timestamp formats to ISO format string.

    Args:
        value: Can be a datetime object, ISO format string, or other value

    Returns:
        ISO format string (YYYY-MM-DDTHH:MM:SS.ffffff)
        If conversion fails, returns current UTC time in ISO format
    """
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, str):
        # Verify it's already in ISO format by attempting to parse it
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return value
        except ValueError:
            logger.warning("Invalid datetime format encountered: %s, using current time", value)
    return datetime.utcnow().isoformat()


def ensure_datetime(value: Any) -> datetime:
    """
    Convert various timestamp formats to datetime object.

    Args:
        value: Can be a datetime object, ISO format string, or other value

    Returns:
        datetime object in UTC
        If conversion fails, returns current UTC time
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            logger.warning("Invalid datetime format encountered: %s, using current time", value)
    return datetime.utcnow()
