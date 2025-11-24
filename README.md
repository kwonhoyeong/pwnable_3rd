# npm 공급망 CVE/EPSS 대응 파이프라인

NPM 생태계 중심의 공급망 취약점을 자동 수집·분석하여 CVSS/EPSS 점수, 위협 인텔리전스, AI 권고안, 대시보드 및 API 응답까지 일괄 생성하는 프로토타입입니다. `MappingCollector → CVSS/EPSS Fetcher → ThreatAgent → Analyzer → QueryAPI/Web UI` 단계로 이어지는 에이전트 파이프라인을 포함합니다.

## 주요 기능
- **멀티 에이전트 오케스트레이션**: `AgentOrchestrator`가 캐시·DB·AI 호출을 묶어 단일 CLI/Worker에서 실행
- **CVE 매핑 + 점수 수집**: Perplexity/NVD/FIRST.org를 통한 CVE, CVSS, EPSS 수집과 폴백 전략
- **AI 기반 심층 분석**: Claude로 Markdown 리포트, GPT-5로 대응 가이드 생성 후 가중치 기반 `risk_score` 산출
- **QueryAPI & Dashboard**: FastAPI + slowapi 인증/레이트리밋, React/Vite 대시보드, 자동 Request ID 주입
- **작업 큐 & 폴백**: Redis `analysis_tasks` 큐, DB/캐시 비활성화 시에도 폴백 데이터로 파이프라인 지속
- **문서/스크립트 세트**: `docs/`, `scripts/`, `demo/`에 환경 구성·헬스체크·검증 도구 포함

## 저장소 구조
```
├── main.py / agent_orchestrator.py   # 파이프라인 CLI & 오케스트레이션
├── worker.py                         # Redis 작업 큐 컨슈머
├── common_lib/                       # 설정, 로거, 캐시, AI 클라이언트, 재시도 유틸
├── mapping_collector/                # 패키지→CVE 매핑 에이전트 (+scheduler, REST)
├── cvss_fetcher/ / epss_fetcher/     # CVSS/EPSS 점수 수집 REST 서비스
├── threat_agent/                     # 위협 검색 + 요약 (Perplexity + Claude)
├── analyzer/                         # GPT-5/Claude 기반 위험 분석 서비스
├── query_api/                        # FastAPI 기반 조회/통계 API
├── web_frontend/                     # Vite/React 대시보드 (Tailwind + React Query)
├── database/                         # PostgreSQL/SQLite 스키마
├── scripts/                          # setup, health_check, verify, init_db 등
├── demo/                             # 샘플 요청 & 빠른 실행 스크립트
├── docs/                             # API, 아키텍처, Docker, JSONB fix 문서
└── tests/                            # 핵심 유틸 단위 테스트와 검증 스크립트
```

## 기술 스택 & 구성 요소
- **Python 3.11 + FastAPI + SQLAlchemy(Async)**: 백엔드 서비스, 파이프라인, QueryAPI
- **Redis 6+**: 캐시 및 작업 큐 (`analysis_tasks`)
- **PostgreSQL 15+/SQLite**: 영속 저장소 (`package_cve_mapping`, `cvss_scores`, `epss_scores`, `threat_cases`, `analysis_results`)
- **AI Clients**: Perplexity, Claude(Anthropic), GPT-5(OpenAI) – `common_lib/ai_clients`
- **Frontend**: React 18, Vite, Tailwind, React Query, axios
- **도구**: docker-compose, slowapi, tenacity, httpx, python-dotenv

## 필수 요구 사항
- Python 3.11+
- Node.js 18+ (Vite dev server)
- PostgreSQL 15+ 및 Redis 6+ (로컬 또는 Docker)
- Docker & docker-compose (전체 시스템 기동 시)
- `pip install -r requirements.txt`
- 프론트엔드: `npm install` (web_frontend)

## 환경 변수 요약 (`.env`, 접두사 `NT_`)
| 변수 | 설명 | 필수 여부 |
|------|------|-----------|
| `POSTGRES_DSN` / `NT_POSTGRES_DSN` | `postgresql+asyncpg://user:pass@host:5432/threatdb` | DB 사용 시 필수 (`NT_ENABLE_DATABASE=true`) |
| `NT_REDIS_URL` | `redis://localhost:6379/0` | 캐시/큐 사용 시 필수 |
| `NT_ENABLE_DATABASE` / `NT_ENABLE_CACHE` | `true`/`false`로 영속성·캐시 토글 | 선택 |
| `NT_ALLOW_EXTERNAL_CALLS` | 외부 API(Perplexity/Claude/GPT/NVD/FIRST) 호출 허용 | 선택 |
| `NT_PERPLEXITY_API_KEY`, `NT_CLAUDE_API_KEY`, `NT_GPT5_API_KEY`, `NVD_API_KEY` | AI·NVD 호출용 토큰 | 기능 사용 시 필요 |
| `NT_QUERY_API_KEYS` | `dev-api-key-123,admin-key-456` 형식으로 QueryAPI 인증 키 | QueryAPI 사용 시 필수 |
| `NT_ENVIRONMENT` | `development`/`production` | 로깅·디버그 제어 |
| `VITE_API_URL`, `VITE_QUERY_API_URL`, `VITE_QUERY_API_KEY` | 웹 프론트엔드 → QueryAPI 연결 정보 | Dashboard 사용 시 필수 |

기본 템플릿은 `.env.example`에 있으며 필요 시 `NT_CACHE_TTL_SECONDS`, `NT_LOG_LEVEL`, `NT_GPT5_MODEL`, `NT_CLAUDE_MODEL` 등을 덮어쓸 수 있습니다.

## 로컬 개발 환경 준비 (수동)
1. **가상환경**  
   ```bash
   python3 -m venv .venv && source .venv/bin/activate
   python3 -m pip install -U pip
   python3 -m pip install -r requirements.txt
   ```
2. **환경 변수**  
   ```bash
   cp .env.example .env
   # Postgres/Redis/AI 키 및 FEATURE 토글 편집
   ```
3. **PostgreSQL & Redis 실행**  
   - Docker 예시  
     ```bash
     docker run -d --name threat-postgres -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:15-alpine
     docker run -d --name threat-redis -p 6379:6379 redis:7-alpine
     ```
   - `database/init-db.sql`을 `psql` 등으로 실행하여 스키마 생성  
4. **플래그 활성화**: DB/캐시 사용 시 `.env`에 `NT_ENABLE_DATABASE=true`, `NT_ENABLE_CACHE=true` 설정  
5. **프론트엔드**  
   ```bash
   cd web_frontend
   npm install
   npm run dev -- --host
   ```

## Docker Compose로 전체 시스템 실행
1. `.env`에서 DB/Redis/AI 키, `NT_QUERY_API_KEYS`, `NVD_API_KEY` 등을 채웁니다.  
2. `docker-compose up -d --build`  
3. 주요 엔드포인트  
   - Frontend: http://localhost:5173  
   - QueryAPI Docs: http://localhost:8004/docs  
   - Redis UI: http://localhost:15672 (RabbitMQ UI, guest/guest)  
   - 각 마이크로서비스 Health: `curl http://localhost:{8000..8004}/health`  
4. Redis 큐에 분석 작업 푸시  
   ```bash
   docker exec npm-threat-redis redis-cli \
     RPUSH analysis_tasks '{"package": "lodash", "version": "4.17.19", "force": true}'
   ```  
5. 종료: `docker-compose down`

## 파이프라인 실행 방법
### 1. CLI 단일 실행 (`main.py`)
```bash
python3 main.py --package lodash \
  --version-range "<4.17.21>" \
  --ecosystem npm \
  --force \
  --skip-threat-agent
```
옵션
- `--ecosystem`: `npm` (기본) / `pip` / `apt`
- `--version-range`: SemVer 또는 `latest`
- `--skip-threat-agent`: 위협 검색 건너뛰기
- `--force`: Redis 캐시 무시

### 2. Redis 작업 큐 + 워커
1. `.env`에 Redis/DB/AI 설정  
2. `python worker.py` 실행 → `analysis_tasks` 큐를 BLPOP로 폴링  
3. 작업 등록: `redis-cli RPUSH analysis_tasks '{"package":"express","version":"latest"}'`  
4. QueryAPI가 `ResourceNotFound`를 만나면 자동으로 동일 큐에 작업을 제출하고 `ANALYSIS_IN_PROGRESS` 응답을 반환합니다.

### 3. QueryAPI 서버
```bash
uvicorn query_api.app.main:app --reload --port 8004
```
- `X-API-Key` 헤더 필수 (`NT_QUERY_API_KEYS` 목록 중 하나)  
- `/api/v1/query`, `/history`, `/stats`, `/health` 제공  
- slowapi로 `/query` 5회/분, `/history` 10회/분 rate limit

### 4. 웹 프론트엔드
```bash
cd web_frontend
npm run dev -- --host 0.0.0.0
```
- `.env.development` 등에 `VITE_API_URL=http://localhost:8004`와 `VITE_QUERY_API_KEY` 설정  
- React Query가 API 응답을 캐싱하고 Request ID 헤더를 자동 생성합니다.

### 5. Helper 스크립트
- `run_pipeline.sh`: 의존성 설치 + CLI 실행
- `demo/run_demo.sh`: `demo/sample_request.json`을 읽어 빠른 데모
- `scripts/setup.sh`: Ubuntu 22.04 전용 종단 간 개발환경 설치
- `scripts/health_check.py`, `scripts/verify_system.py`: 서비스 및 API 상태 확인
- `scripts/verify_fixes.py`, `scripts/demo_check.py`: 회귀 검증

## 데이터 파이프라인 흐름
1. **MappingCollector (`mapping_collector/app`)**  
   - Perplexity → NVD/파생 Feed 순으로 CVE 조회  
   - `MappingService.fetch_cves`는 `normalize_cve_ids`로 정규화 후 Redis/DB 저장
2. **CVSS/EPSS Fetcher (`cvss_fetcher/app`, `epss_fetcher/app`)**  
   - `asyncio.gather`로 병렬 수집, NVD/FIRST.org 호출 실패 시 폴백  
   - 결과는 Redis 캐시 + `cvss_scores`/`epss_scores`에 upsert
3. **ThreatAgent (`threat_agent/app`)**  
   - Perplexity 검색 → Claude 요약 → Sanitization → JSONB 저장  
   - `--skip-threat-agent` 시 안전한 기본 사례 반환
4. **Analyzer (`analyzer/app`)**  
   - Claude로 엔터프라이즈 리포트(영→한), GPT-5로 권고  
   - `risk_score = CVSS*0.4 + (EPSS*10)*0.3 + AI_SCORE*0.3` (AI_SCORE: CRIT 9.5, HIGH 7.5, MED 5.0, LOW 2.0)
5. **Persistence & Cache**  
   - 각 단계 결과를 PostgreSQL에 upsert (비활성 시 인메모리 폴백)  
   - Redis 네임스페이스 예: `mapping:npm:lodash:latest`, `analysis:npm:lodash:latest:CVE-2023-1234`
6. **QueryAPI/Web Frontend**  
   - `QueryService`가 Redis 캐시 조회 → DB 조회 → 미존재 시 분석 작업 제출 → 최대 30초 폴링  
   - 응답에는 `risk_score`, `risk_label(P1/P2/P3)`가 포함되며 대시보드에서 시각화

## 서비스 모듈 요약
| 모듈 | 역할 | 주요 파일 |
|------|------|-----------|
| `mapping_collector/app` | 패키지-CVE 매핑 REST & 스케줄러 | `service.py`, `scheduler.py` |
| `cvss_fetcher/app`, `epss_fetcher/app` | CVSS/EPSS 점수 REST API | `service.py`, `repository.py` |
| `threat_agent/app` | 위협 검색/요약 + Sanitization | `services.py`, `prompts.py` |
| `analyzer/app` | AI 리포트, 권고, 가중치 스코어링 | `service.py`, `prompts.py` |
| `query_api/app` | FastAPI + 인증 + Rate limit | `main.py`, `service.py`, `repository.py` |
| `web_frontend` | React/Vite 대시보드 | `src/pages/DashboardPage.tsx`, `src/api/` |
| `common_lib` | 설정, 로깅, 캐시, AI 클라이언트, 재시도 | `config.py`, `cache.py`, `ai_clients/` |

## QueryAPI & Web UI
- **엔드포인트**:  
  - `GET /api/v1/query?package=<name>&version=<range>` 또는 `?cve_id=<id>`  
  - `GET /api/v1/history?skip=&limit=`  
  - `GET /api/v1/stats`  
  - `GET /health`
- **응답 표준**: `{ "error": { "code": "...", "message": "...", "details": {...} } }` 형태의 에러 봉투 및 `X-Request-ID` 헤더
- **웹 UI**: `SearchBar`, `StatsCards`, `RecentScansTable` 조합으로 패키지 검색, 분석 대기 상태(`ANALYSIS_IN_PROGRESS`) 안내, Request ID 자동 부여

## 분석 작업 큐 & 자동 트리거
- Redis 리스트 `analysis_tasks` 사용 (`worker.py`, `query_api/app/redis_ops.py`)
- QueryAPI가 데이터 미존재 시 `submit_analysis_job`을 호출하여 패키지/버전/force 파라미터로 작업 푸시 → 워커가 `AgentOrchestrator`를 실행
- `scripts/inject_task.py`로 수동 테스트 가능

## 테스트 / 진단 / 검증
- `pytest tests/test_perplexity_parsers.py`
- `python scripts/health_check.py` : API 키·헬스·캐시 동작 체크
- `python scripts/verify_system.py` : 전체 시스템 검증 루틴
- `npm test` (web_frontend) – 필요 시 구성
- GitHub Actions 등 외부 CI에선 `docker-compose` 조합 또는 `scripts/setup.sh` 활용 가능

## 시스템 상태
- 다중 에이전트 파이프라인, Redis 캐시, PostgreSQL 영속화, AI 폴백 전략, QueryAPI 인증·레이트리밋, React 대시보드, Request ID 미들웨어, JSONB 위협 사례 저장 등 **정상 동작**
- Redis/DB/AI 비활성 시에도 폴백 데이터를 반환하여 사용자 영향 최소화

## 알려진 제한 사항
- Redis/DB가 꺼져 있을 때 성능 저하 (캐시 및 영속 저장 비활성화)
- `NT_ALLOW_EXTERNAL_CALLS=false` 상태에서는 Perplexity/Claude/GPT 호출이 전부 폴백 메시지로 대체
- `NT_GPT5_API_KEY`가 없으면 Analyzer 권고안/리포트가 기본 문구로 교체
- QueryAPI는 total count 대신 `total_returned`만 제공 (페이지네이션 전체 개수 미포함)
- Docker Compose는 개발용 설정이며 프로덕션 배포 시 별도 보안 강화를 권장

## 문서 모음
- `SETUP.md`: 팀 개발환경 세팅 가이드
- `docs/ARCHITECTURE.md`: 전체 데이터 흐름, AI 역할, 최근 개선 사항
- `docs/API.md`: 각 마이크로서비스 REST 명세 및 인증/레이트리밋 설명
- `docs/DOCKER.md`: Docker 협업 환경 가이드
- `docs/JSONB_FIX_EXPLANATION.md`: ThreatAgent JSONB 직렬화 이슈 분석
- `manual_checklist.md`: 수동 점검 체크리스트

## 데이터베이스 접속 방법 (Database Access)
Docker 컨테이너로 실행 중인 PostgreSQL 데이터베이스에 접속하는 방법입니다.

### 1. 터미널 접속 (CLI)
```bash
docker exec -it npm-threat-postgres psql -U postgres -d npm_threat_db
```

### 2. GUI 도구 접속 (DBeaver, TablePlus 등)
- **Host**: `localhost`
- **Port**: `15432`
- **Database**: `npm_threat_db`
- **User**: `postgres`
- **Password**: `postgres`

### 3. 주요 테이블 확인
```sql
\dt                  -- 테이블 목록 보기
SELECT * FROM analysis_results LIMIT 5;  -- 분석 결과 확인
```
