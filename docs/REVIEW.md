# Backend & Frontend Review Report

_Last updated: 2025-02-15_

## 1. Backend Review

### 1.1 QueryAPI (`query_api/app`)
- **Missing Authentication & Rate Limiting** (`main.py:18-172`): All endpoints are publicly accessible; add API-key/JWT middleware and rate limiting (e.g., `slowapi`).
- **Debug Logging in Production** (`main.py:72,102,124`): Persistent debug logs dump session repr; guard with configuration or remove before release.
- **Repository Layer** (`repository.py:20-185`):
  - Uses raw SQL but lacks SQL injection protection for `package`/`cve_id` beyond simple binding—ensure validation.
  - `get_history` selects `risk_score` but UI expects `priority_score`; align schema vs API contract.
  - No pagination metadata beyond `total_returned`; consider total count for UI.
- **Service Layer** (`service.py:16-122`):
  - Cache key collision risk when both package & cve_id provided; currently raises `ValueError` but API allows specifying both.
  - Priority calculation ignores AI weighted `risk_score`; consider surfacing both.
  - No cache busting when DB entries change; stale data persists until TTL.

### 1.2 ThreatAgent (`threat_agent/app/services.py`)
- **Language Prompting**: Sanitization ensures Korean summaries but `ThreatSummaryService` prompt lacks explicit bilingual requirement; documentation claims "한국어/영어" yet code may not enforce.
- **Severity Extraction**: `_extract_severity` derived severity is never stored; lost context.
- **Error Handling**: Exceptions from Perplexity/Claude propagate without retries/backoff; wrap with `tenacity`.

### 1.3 Common Issues
- **Secrets in `.env`**: Real API keys are committed locally (`.env`); ensure this file is gitignored before pushing.
- **Docker Compose**: `agent-orchestrator` build context references `analyzer/Dockerfile` which might be incorrect for orchestrator runtime.

### 1.4 Recommendations
1. Introduce authentication/authorization middleware on QueryAPI.
2. Align backend response models with frontend expectations (`risk_score` vs `priority_score`).
3. Persist AI-derived `risk_score` and expose via API.
4. Add retries/backoff for external AI calls and structured error envelopes.
5. Harden Docker configuration (non-root users, health endpoints).

## 2. Frontend Review

### 2.1 API Layer (`web_frontend/src/api/endpoints.ts`)
- Type `CVEDetail.priority_score` is treated as risk score; backend sends `priority_score` but history endpoint returns `risk_score`. Need unified interface.
- `HistoryResponse` expects `total_returned`, but API uses `total_returned` while components expect `total`; ensure consistent naming.

### 2.2 Dashboard Components
- `RecentScansTable.tsx:52-86`: `risk_score.toFixed(1)` guarded correctly, but upstream converters pass `priority_score` vs actual numeric risk.
- `DashboardPage.tsx`: Search query ignores user-supplied version parameter; always queries package only.
- Error banners rely on `isError` but not on `error` details; add `getErrorMessage`.

### 2.3 Build/Dev Config
- `vite.config.ts` proxies `/api` to `localhost:8004`; ensure backend is mounted at same path in production (currently unspecified in docs).
- `.env` for Vite missing; documentation should instruct setting `VITE_QUERY_API_BASE_URL`.

### 2.4 Recommendations
1. Update API converters to distinguish between `risk_score` (AI weighted) and `priority_score`.
2. Pass `version` into backend query when provided.
3. Surface backend errors in UI via toast/banner.
4. Document Vite environment variables and proxy expectations.

## 3. Documentation Updates
- README should include the new review highlights, current backend auth gaps, and frontend/API schema alignment tasks.
- Add runbooks for restarting Docker services after `.env` changes.
