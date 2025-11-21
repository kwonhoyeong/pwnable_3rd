# npm 공급망 CVE/EPSS 대응 파이프라인 (NPM Supply Chain CVE/EPSS Response Pipeline)

## Repository Layout
```
  ├── main.py
  ├── common_lib/
  ├── mapping_collector/
  ├── cvss_fetcher/
  ├── epss_fetcher/
  ├── threat_agent/
  ├── analyzer/
  ├── query_api/
  ├── web_frontend/
  ├── demo/
  └── .env.example
```

## Requirements
- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Node.js 18+ (Vite 기반 Web Frontend)
- FastAPI 0.121.x, Uvicorn 0.3x, React 18.3.x (see `requirements.txt`, `web_frontend/package.json`)

## Setup
1. `python3 -m venv .venv && source .venv/bin/activate`
2. `python3 -m pip install -r requirements.txt`
3. `cp .env.example .env` 후 AI API 키와 데이터베이스/캐시 DSN을 설정
4. (선택 사항) `npm install` inside `web_frontend/`

## Environment Configuration (.env file)

**REQUIRED**: You must create a `.env` file in the project root with the following variables:

```dotenv
# Database & Cache
NT_POSTGRES_DSN=postgresql+asyncpg://<user>:<password>@localhost:5432/threatdb
NT_REDIS_URL=redis://localhost:6379/0

# AI API Keys (at least one is required for GPT-based analysis)
NT_GPT5_API_KEY=sk-REPLACE_WITH_YOUR_OPENAI_API_KEY
NT_PERPLEXITY_API_KEY=your-perplexity-key-here
NT_CLAUDE_API_KEY=your-claude-key-here

# Feature toggles (set to true when infrastructure is available)
NT_ALLOW_EXTERNAL_CALLS=false
NT_ENABLE_DATABASE=false
NT_ENABLE_CACHE=false
```

### ⚠️ Important Notes on API Keys

- **`NT_GPT5_API_KEY` is required for AI-powered vulnerability analysis.**
  - If this key is **missing or invalid**, the system will:
    - Log a clear ERROR message at startup: `"NT_GPT5_API_KEY is not set or empty"`
    - Skip GPT API calls and use fallback analysis with the message:
      ```
      "AI 분석 실패로 수동 검토 필요(Manual review required due to AI failure)."
      ```
  - The pipeline will still complete successfully, but analysis quality will be limited.

- **Authentication errors (401/400)**: Check your API key validity if you see these errors in logs.

## Run main.py locally
1. PostgreSQL과 Redis를 실행하세요(Start PostgreSQL & Redis).
   - PostgreSQL에서 `threatdb` 데이터베이스를 만든 후 각 모듈의 `db/schema.sql`을 순서대로 실행합니다(`psql -f mapping_collector/db/schema.sql` 등).
   - Redis는 기본 포트(6379)로 실행하면 됩니다.
2. `.env` 파일에 위와 같이 접속 정보와 API 키를 설정합니다(Fill in connection details and API keys).
3. 가상환경을 활성화한 상태에서 `python3 main.py --package lodash` 명령을 실행하면 파이프라인이 동작합니다.

## Quick Start
```bash
# 가장 빠르게 전체 시스템 실행하는 방법
python3 main.py --package lodash

# Force fresh GPT-based analysis (bypass cache)
python3 main.py --package lodash --force

# Skip threat agent collection
python3 main.py --package lodash --skip-threat-agent
```

### CLI Options
- `--package`: (Required) Target npm package name
- `--version-range`: (Optional) Version range to analyze (default: "latest")
- `--force`: Bypass all caches and force fresh API calls (including GPT analysis)
- `--skip-threat-agent`: Skip threat case collection and use fallback data

## Helper Script (`run_pipeline.sh`)
```bash
# 최초 실행 시 의존성 설치까지 수행(Install deps on first run)
bash run_pipeline.sh --package lodash --install-deps

# ThreatAgent 단계를 생략하고 실행(Skip threat collector)
bash run_pipeline.sh --package lodash --skip-threat-agent

# 실행 전 실행 권한을 부여할 수도 있습니다(optional chmod)
chmod +x run_pipeline.sh
./run_pipeline.sh --package lodash
```
> `.env` 파일이 준비되어 있어야 하며(PostgreSQL/Redis), 필요한 경우 `--python`으로 다른 인터프리터를 지정할 수 있습니다.

## Pipeline at a Glance
1. `AgentOrchestrator` → 각 에이전트 실행 순서를 정의하고 진행 상황을 브로드캐스트합니다.
2. MappingAgent → 패키지/버전 입력에 대한 CVE를 캐시 조회 후 수집합니다.
3. CVSSAgent & EPSSAgent → `asyncio.gather`로 동시에 실행되며 점수를 조회하고 캐싱합니다.
4. ThreatAgent → 필요 시 위협 사례를 모으고, `--skip-threat-agent` 옵션 시 안전한 기본값으로 대체합니다.
5. Analyzer → Claude + GPT5를 사용하여 **엔터프라이즈 Markdown 리포트**를 생성하고, `CVSS*0.4 + (EPSS*10)*0.3 + AI Score*0.3` 가중치 기반 `risk_score`를 계산합니다.
6. QueryAPI/WebFrontend → Redis 캐시+PostgreSQL을 조회해 `/api/v1/query`, `/api/v1/history`, `/api/v1/stats` 데이터를 노출하고 React 대시보드에서 시각화합니다.

### QueryAPI Endpoints (v1)
- `GET /api/v1/query?package=<name>|cve_id=<id>`: 패키지/CVE 단건 조회 (우선순위 스코어 포함)
- `GET /api/v1/history?skip=0&limit=10`: AI 분석 이력 + `risk_score` 목록
- `GET /api/v1/stats`: 위험도 분포(critical/high/medium/low/unknown) 및 전체 스캔 수
- 모든 응답은 `X-Request-ID` 헤더·JSON 에러 포맷(`{"error": {...}}`)을 따릅니다.

### Web Frontend (Vite/React 18.3)
- Tailwind 기반 디자인 토큰(`web_frontend/src/styles/`)과 `components/ui`에서 버튼/배지/카드 등 원자 컴포넌트 정의
- `DashboardPage`는 `SearchBar`, `StatsCards`, `RiskDistributionChart`, `RecentScansTable`을 조합해 API 데이터를 시각화
- `web_frontend/src/api/client.ts`는 Request ID 헤더, `VITE_API_URL`/`VITE_QUERY_API_URL` 환경 변수를 지원합니다.

## System Status

### Working Features ✅
- Multi-agent pipeline orchestration
- CVE/CVSS/EPSS data collection with fallback mechanisms
- Threat intelligence aggregation (when API keys configured)
- AI-powered Markdown 분석 + 가중치 기반 위험 점수 산출
- PostgreSQL persistence with automatic failover to in-memory mode
- Redis caching with graceful degradation when unavailable
- QueryAPI `/query` + `/history` + `/stats` endpoints with request ID middleware
- React dashboard (Vite) + REST API client with automatic `X-Request-ID`
- Robust error handling and logging

### Known Limitations
- **Redis**: Optional - system works without it but with reduced performance
- **PostgreSQL**: Optional - data persists in-memory if DB unavailable (warning logged)
- **API Keys**: System runs with fallback data when keys are missing:
  - Missing `NT_PERPLEXITY_API_KEY`: Uses fallback threat cases
  - Missing `NT_GPT5_API_KEY`: Uses fallback analysis recommendations
  - Missing external API access: Uses default EPSS/CVSS scores (0.0)
- **Feature toggles**: External APIs/Redis/PostgreSQL are disabled by default for CLI tests.
  - Set `NT_ALLOW_EXTERNAL_CALLS=true` to hit live AI/Perplexity endpoints.
  - Set `NT_ENABLE_DATABASE=true` when PostgreSQL is reachable.
  - Set `NT_ENABLE_CACHE=true` when Redis is available.

### Recent Fixes (2025-02-15)
- ✅ MappingScheduler uses AsyncSession safely (no more `async_generator` context errors)
- ✅ Query prioritization respects uppercase `CRITICAL/HIGH` values for accurate dashboards
- ✅ Frontend API client honors `VITE_API_URL`/`VITE_QUERY_API_URL` and backfills `X-Request-ID`
- ✅ Dependencies bumped (FastAPI 0.121.x, Uvicorn 0.38.x, React 18.3.x, axios 1.13.x, etc.)
- ✅ Docs refreshed: Weighted scoring, new endpoints, frontend stack summary

## Documentation
- 더 자세한 내용은 `docs/ARCHITECTURE.md`, `docs/API.md` 참고
- Recent improvements: See `docs/ARCHITECTURE.md` → "Latest Fixes (2025-11-17)"

## License
- MIT License
