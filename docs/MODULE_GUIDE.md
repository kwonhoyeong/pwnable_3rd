# Module Structure Guide

This document describes the organization and responsibilities of all modules in the CVE analysis pipeline.

## Directory Structure

```
src/core/
├── Core utilities and abstractions for the pipeline
├── agents/          Agent patterns and base classes
├── data/            Data serialization and validation
├── io/              Input/output operations
├── utils/           General-purpose utilities
├── errors.py        Exception types
├── context.py       Execution context
└── logger.py        Logging configuration
```

## Module Reference

### Core Modules

#### `src.core.errors`
**Purpose**: Define custom exception types for error classification and recovery.

**Key Classes**:
- `PipelineError`: Base exception for all pipeline errors
- `ExternalAPIError`: External API call failures (transient, use fallback)
- `DataValidationError`: Input validation failures (permanent, reject input)
- `FallbackError`: Fallback data generation failures (critical issue)

**Usage**:
```python
from src.core.errors import ExternalAPIError
try:
    result = await fetch_from_external_api()
except ExternalAPIError as e:
    logger.warning("API failed: %s", e)
    result = get_fallback_data()
```

#### `src.core.context`
**Purpose**: Shared execution context for pipeline stages.

**Key Class**:
- `PipelineContext`: Dataclass holding execution state

**Usage**: Pass context through pipeline stages to share state without deep coupling.

#### `src.core.logger`
**Purpose**: Centralized logging configuration.

**Functions**:
- `get_logger(name)`: Get a configured logger instance

**Usage**:
```python
from src.core.logger import get_logger
logger = get_logger(__name__)
logger.info("Pipeline started for %s", package)
```

#### `src.core.fallback`
**Purpose**: Generate synthetic fallback data when external services fail.

**Key Class**:
- `FallbackProvider`: Static methods for generating fallback data

**Methods**:
- `fallback_cves(package)`: Generate synthetic CVE list
- `fallback_epss(cve_id)`: Generate neutral EPSS score (0.5)
- `fallback_cvss(cve_id)`: Generate neutral CVSS score (5.0)
- `fallback_threat_cases(payload)`: Generate empty threat cases
- `fallback_analysis(payload)`: Generate Medium risk analysis

**Usage**:
```python
from src.core.fallback import FallbackProvider
provider = FallbackProvider()
cves = provider.fallback_cves("lodash")
```

### Agent Submodule (`src.core.agent`)

#### `src.core.agent`
**Purpose**: Define base classes and protocols for all agents.

**Key Classes**:
- `BaseAgent`: Abstract base for all agents
  - `_get_cached()`: Retrieve from cache with force bypass
  - `_set_cache()`: Store in cache
  - `_progress()`: Send progress updates
  - `execute()`: Abstract method for agent logic

- `SingleItemAgent`: Base for single-item operations (Mapping, Threat, Analysis)
- `BatchAgent`: Base for batch operations with optimization (EPSS, CVSS)

**Inheritance Pattern**:
```python
class MyAgent(SingleItemAgent):
    async def execute(self, force=False, progress_cb=None):
        # Check cache, execute service call, update cache
        pass
```

#### `src.core.agent_helpers`
**Purpose**: Helper functions for agent implementations.

**Functions**:
- `safe_call(coro, fallback, step, progress_cb)`: Execute with automatic fallback
- `build_cache_key(base, *parts)`: Generate consistent cache keys
- `filter_missing_items(full_list, cached_results)`: Find missing batch items

**Usage**:
```python
from src.core.agent_helpers import safe_call, build_cache_key

result = await safe_call(
    service.fetch_data(),
    fallback=lambda: default_data,
    step="STEP_NAME",
    progress_cb=progress_callback
)

cache_key = build_cache_key("epss", package, version)
```

### Data Submodule (`src.core.serialization`)

#### `src.core.serialization.threat_case`
**Purpose**: Serialize ThreatCase objects to JSON-compatible dicts.

**Functions**:
- `serialize_threat_case(case)`: Convert ThreatCase → dict
  - Handles Pydantic v1/v2 compatibility
  - Converts HttpUrl to string
  - Normalizes timestamps to ISO format

#### `src.core.serialization.pipeline_result`
**Purpose**: Serialize complete pipeline results.

**Functions**:
- `serialize_pipeline_result(package, version_range, cve_id, epss_record, cvss_record, threat_response, analysis_output)`: Create comprehensive result dict
  - Combines EPSS, CVSS, threat cases, and analysis
  - Handles None values gracefully
  - Returns JSON-serializable output

**Result Structure**:
```python
{
    "package": str,
    "version_range": str,
    "cve_id": str,
    "epss": {"epss_score": float|None, "collected_at": str},
    "cvss": {"cvss_score": float|None, "vector": str|None, "collected_at": str},
    "cases": [{"source": str, "title": str, ...}],
    "analysis": {"risk_level": str, "recommendations": [str], ...}
}
```

### IO Submodule (`src.core.persistence`)

#### `src.core.persistence.db_store`
**Purpose**: Manage database persistence for pipeline results.

**Key Class**:
- `PersistenceManager`: Unified interface for database operations

**Methods**:
- `persist_mappings(package, version_range, cve_ids)`: Store CVE mappings
- `persist_epss_scores(cve_results)`: Store EPSS scores
- `persist_cvss_scores(cve_results)`: Store CVSS scores
- `persist_threat_cases(cve_id, package, version_range, cases)`: Store threat cases
- `persist_analysis(cve_id, risk_level, recommendations, summary, generated_at)`: Store analysis

**Usage**:
```python
from src.core.persistence import PersistenceManager

manager = PersistenceManager(session)
await manager.persist_epss_scores(epss_results)
await manager.persist_analysis(cve_id, "High", [...], "Summary", now)
```

### Utils Submodule (`src.core.utils`)

#### `src.core.utils.timestamps`
**Purpose**: Handle timestamp normalization and conversion.

**Functions**:
- `normalize_timestamp(value)`: Convert to ISO string
  - Accepts: datetime, ISO string, None (uses current time)
  - Returns: ISO string or current time

- `ensure_datetime(value)`: Convert to datetime object
  - Accepts: datetime, ISO string, None (uses current time)
  - Returns: datetime object
  - Falls back to current time on invalid format

**Usage**:
```python
from src.core.utils.timestamps import normalize_timestamp, ensure_datetime

iso_str = normalize_timestamp(datetime.now())
dt = ensure_datetime("2025-11-18T10:00:00Z")
```

## Import Patterns

### Recommended Imports

**From core utilities**:
```python
from src.core.fallback import FallbackProvider
from src.core.utils.timestamps import normalize_timestamp, ensure_datetime
from src.core.agent_helpers import safe_call, build_cache_key
```

**From agents**:
```python
from src.core.agent import BaseAgent, SingleItemAgent, BatchAgent
```

**From serialization**:
```python
from src.core.serialization import serialize_threat_case, serialize_pipeline_result
```

**From persistence**:
```python
from src.core.persistence import PersistenceManager
```

### Avoid Circular Imports

- Don't import `agent_orchestrator` from core modules
- Don't create dependencies between external services
- Use dependency injection for service instances

## Adding New Modules

When adding new functionality:

1. **Small utility**: Add to existing `utils/` submodule
2. **Agent-related**: Extend `BaseAgent` in `agents/` submodule
3. **Data handling**: Add to `serialization/` submodule
4. **Database operations**: Add to `persistence/` submodule
5. **New category**: Create new submodule with `__init__.py` and internal modules

## Module Dependencies

```
agent_orchestrator.py
    ↓
src.core (top-level)
    ├→ fallback
    ├→ context
    ├→ logger
    ├→ errors
    ├→ agent (agents/)
    │   └→ agent_helpers
    ├→ serialization (data/)
    │   ├→ threat_case
    │   └→ pipeline_result
    ├→ persistence (io/)
    │   └→ db_store
    └→ utils (utils/)
        └→ timestamps
```

## Testing Module Organization

```
tests/
├── conftest.py                    # Shared fixtures
├── test_smoke_pipeline.py         # End-to-end tests
├── test_core_fallback.py          # Fallback provider tests
└── test_core_timestamps.py        # Timestamp utility tests
```

Future test additions:
- `test_core_serialization.py`: Serialization module tests
- `test_core_agent_helpers.py`: Agent helper function tests
- `test_core_persistence.py`: Persistence manager tests

## Module Stability

### Stable (Low change frequency)
- `errors.py`: Exception definitions rarely change
- `logger.py`: Logging setup is stable
- `utils/timestamps.py`: Timestamp handling is stable
- `context.py`: Execution context structure rarely changes

### Medium (Regular enhancements)
- `fallback.py`: New fallback types may be added
- `persistence/`: New persistence methods may be added
- `serialization/`: New serialization formats may be added

### Evolving (Frequent changes during development)
- `agent.py`: Agent patterns evolve as implementations grow
- `agent_helpers.py`: New helper functions as patterns emerge

## Best Practices

1. **Import at module level**: Avoid circular imports by importing at function level only when necessary
2. **Use __all__**: Explicitly export public APIs from `__init__.py`
3. **Add docstrings**: Document module purpose and key classes
4. **Type hints**: Use type annotations for clarity
5. **Error handling**: Use custom exceptions from `errors.py`
6. **Logging**: Use `get_logger(__name__)` for module logging
7. **Testing**: Write tests in corresponding `test_*.py` files

## Future Refactoring

Potential improvements for future phases:
- Extract service interfaces as protocols
- Create factory classes for complex object creation
- Add middleware/decorator patterns for cross-cutting concerns
- Consider plugin architecture for extensible components
