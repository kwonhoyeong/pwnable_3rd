"""Core utilities and abstractions for the CVE analysis pipeline."""

# Error handling
from src.core.errors import (
    ExternalAPIError,
    PipelineError,
    DataValidationError,
    FallbackError,
)

# Core components
from src.core.fallback import FallbackProvider
from src.core.context import PipelineContext

# Utilities
from src.core.utils.timestamps import normalize_timestamp, ensure_datetime

# Agents
from src.core.agents import BaseAgent, SingleItemAgent, BatchAgent
from src.core.agents import safe_call, build_cache_key, filter_missing_items

# Data handling
from src.core.data import serialize_threat_case, serialize_pipeline_result

# IO operations
from src.core.io import PersistenceManager

__all__ = [
    # Error classes
    "PipelineError",
    "ExternalAPIError",
    "DataValidationError",
    "FallbackError",
    # Core components
    "FallbackProvider",
    "PipelineContext",
    # Utilities
    "normalize_timestamp",
    "ensure_datetime",
    # Agents
    "BaseAgent",
    "SingleItemAgent",
    "BatchAgent",
    "safe_call",
    "build_cache_key",
    "filter_missing_items",
    # Data handling
    "serialize_threat_case",
    "serialize_pipeline_result",
    # IO
    "PersistenceManager",
]
