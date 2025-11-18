# CVE Analysis Pipeline - Architecture Overview

## High-Level Flow

```
main.py (CLI entrypoint)
    ↓
AgentOrchestrator.orchestrate_pipeline()
    ├─→ MappingService.fetch_cves()              [OSV API]
    ├─→ EPSSService.fetch_score()                 [Perplexity]
    ├─→ CVSSService.fetch_score()                 [Perplexity]
    ├─→ ThreatAggregationService.collect()        [Perplexity + Claude]
    └─→ AnalyzerService.analyze()                 [GPT-5 + Claude]
```

## Module Responsibilities

### Core Modules (`common_lib/`)
- **config.py**: Pydantic Settings for environment variables (DB, Cache, API keys)
- **logger.py**: Python logging setup and named logger access
- **cache.py**: Redis-backed cache with optional in-memory fallback
- **db.py**: SQLAlchemy session management (PostgreSQL)
- **ai_clients/**: HTTP wrappers for external AI APIs (Claude, GPT-5, Perplexity)

### Agent Modules (data flow: service → repository → DB)

Each agent follows the pattern: **Service** (business logic) → **Repository** (persistence) → **Database**

1. **mapping_collector/** — Fetch CVE IDs for a package
   - `service.py`: Query OSV API, resolve npm package versions
   - `models.py`: `PackageInput` (in), CVE list (out)
   - `repository.py`: Persist CVE mappings to DB

2. **epss_fetcher/** — Score CVEs by exploit prediction
   - `service.py`: Query Perplexity for EPSS scores (0.0–1.0)
   - `models.py`: `EPSSInput` (CVE ID), `EPSSRecord` (score + timestamp)
   - `repository.py`: Persist EPSS scores to DB

3. **cvss_fetcher/** — Score CVEs by severity
   - `service.py`: Query Perplexity for CVSS v3 base scores (0.0–10.0) and vectors
   - `models.py`: `CVSSInput` (CVE ID), `CVSSRecord` (score + vector + timestamp)
   - `repository.py`: Persist CVSS scores to DB

4. **threat_agent/** — Collect known exploit cases
   - `services.py`: Search Perplexity for real-world attack cases, summarize with Claude
   - `models.py`: `ThreatInput` (CVE + package), `ThreatCase`, `ThreatResponse`
   - `repository.py`: Persist threat cases to DB

5. **analyzer/** — Synthesize scores and cases into risk level + recommendations
   - `service.py`: Rule-based risk classification, AI-driven recommendations (GPT-5) and summaries (Claude)
   - `models.py`: `AnalyzerInput` (EPSS + CVSS + cases), `AnalyzerOutput` (risk_level + recommendations + summary)
   - `repository.py`: Persist analysis results to DB

### Orchestration (`agent_orchestrator.py`)

- Coordinates pipeline: calls each agent in sequence or parallel
- Handles caching (in-memory or Redis)
- Manages database sessions and transactions
- Provides fallback values if an agent fails
- Serializes results and persists to DB (if enabled)
- Returns final JSON result to CLI

### Entry Points

- **main.py**: CLI entrypoint
  - Parses arguments (--package, --version-range, --skip-threat-agent, --force)
  - Creates event loop, runs pipeline, prints JSON result, graceful shutdown

- **query_api/**: FastAPI service for historical queries (future scope)
  - Retrieve past pipeline results from DB
  - Filter by package, CVE, date range, risk level

## Configuration

Via `.env` file using Pydantic Settings:

- **Database**: `NT_POSTGRES_DSN` (optional; if not set, in-memory fallback)
- **Cache**: `NT_REDIS_URL` (optional; if not set, in-memory cache)
- **Feature toggles**: `NT_ENABLE_DATABASE`, `NT_ENABLE_CACHE`, `NT_ALLOW_EXTERNAL_CALLS`
- **API Keys**: `NT_CLAUDE_API_KEY`, `NT_GPT5_API_KEY`, `NT_PERPLEXITY_API_KEY`

## Error Handling & Fallback Strategy

Each agent has a fallback function to return synthetic data if external API fails:
- Mapping: return a synthetic CVE based on package hash
- EPSS: return neutral score (0.5)
- CVSS: return neutral score (5.0)
- Threat: return placeholder case
- Analyzer: return "Medium" risk with canned recommendations

Fallbacks allow the pipeline to complete even if some APIs are unavailable.

## Known Limitations & Future Improvements

- No retry logic with exponential backoff for transient failures
- Error classification is minimal (all errors trigger fallback)
- No circuit breaker pattern for API calls
- Limited test coverage (one standalone serialization test)
- Agent discovery/plugin system not yet implemented
