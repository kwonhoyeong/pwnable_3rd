# ARCHITECTURE

이 문서는 `npm 공급망 CVE/EPSS 대응 파이프라인`의 전체 아키텍처를 설명합니다. CLI 오케스트레이터, 분리된 마이크로서비스, AI 백엔드, QueryAPI, 웹 대시보드가 어떻게 맞물려 동작하는지 구조적 관점에서 정리했습니다.

---

## 1. 시스템 개요
- **목표**: npm (및 확장된 pip/apt) 패키지에 대한 CVE 매핑, CVSS/EPSS 점수, 위협 인텔리전스, AI 분석, API/대시보드 노출까지 자동화합니다.
- **패턴**: Redis 캐시와 PostgreSQL 영속 저장소를 활용하는 event-driven agent pipeline + REST API + React SPA.
- **핵심 실행 경로**  
  `AgentOrchestrator → MappingCollector → CVSSFetcher & EPSSFetcher → ThreatAgent → Analyzer → QueryAPI → Web Frontend`

| 계층 | 역할 | 주요 파일 |
|------|------|-----------|
| Pipeline Orchestrator | CLI/워커 진입점, 단계별 캐시 & DB 저장 | `agent_orchestrator.py`, `main.py`, `worker.py` |
| Services (Collectors/Fetchers) | CVE/점수/위협/분석 HTTP API | `mapping_collector/`, `cvss_fetcher/`, `epss_fetcher/`, `threat_agent/`, `analyzer/` |
| Data Serving | 인증·Rate limit·캐시 연계 QueryAPI와 React 대시보드 | `query_api/`, `web_frontend/` |
| Common Layer | 설정, 로깅, Redis/DB 유틸, AI 클라이언트, 재시도 규칙 | `common_lib/` |

---

## 2. 파이프라인 실행 플로우

### 2.1 초기화
1. `AgentOrchestrator` (CLI/worker)이 `.env`를 로드하고 `AsyncCache`, DB 세션(`common_lib.db.get_session`) 컨텍스트, 각 서비스 인스턴스를 생성합니다.
2. `--force`, `--skip-threat-agent`, `--ecosystem` 플래그로 캐시 정책·생태계를 제어합니다.

### 2.2 CVE 매핑 (MappingCollector)
1. 캐시 키 `mapping:{ecosystem}:{package}:{version}`을 조회합니다.
2. 캐시 미스 시 `mapping_collector.app.service.MappingService`가 Perplexity 검색 → NVD/파생 feed 순으로 CVE 목록을 조회합니다.
3. 결과를 Redis 캐시, `package_cve_mapping` 테이블에 저장하고 반환합니다.

### 2.3 점수 수집 (CVSS/EPSS)
1. `asyncio.gather`로 `CVSSService`, `EPSSService`를 병렬 호출합니다.
2. 캐시 (`cvss:*`, `epss:*`)에서 이미 수집된 점수를 재사용하고, 누락된 항목만 외부 API(NVD, FIRST.org)를 호출합니다.
3. 실패 시 `_fallback_cvss/_fallback_epss`로 None/기본값을 주입하고 Redis 및 `cvss_scores / epss_scores`에 upsert합니다.

### 2.4 위협 인텔리전스 (ThreatAgent)
1. Skip 플래그가 없으면 캐시(`threat:*`)를 확인 후 Perplexity 검색 → Claude 요약을 실행합니다.
2. `_sanitize_text/_sanitize_source`로 AI 출력의 HTML, 제어 문자, 잘못된 URL을 제거하고 JSONB 저장용 dict로 직렬화합니다.
3. Redis 캐시와 `threat_cases` 테이블에 저장합니다.

### 2.5 분석 (Analyzer)
1. 입력(CVE, CVSS, EPSS, 위협 사례)을 `AnalyzerService`로 전달합니다.
2. Claude가 영어 리포트를 생성하고 규칙 기반 한국어 번역을 수행합니다.
3. GPT-5가 대응 권고를 생성하고, `WeightedScoringEngine`이 `risk_score = CVSS*0.4 + (EPSS*10)*0.3 + AI_SCORE*0.3`을 계산합니다.
4. 결과를 Redis 캐시(`analysis:*`)와 `analysis_results`에 저장합니다.

### 2.6 데이터 제공 (QueryAPI & Web UI)
1. QueryAPI (`FastAPI` + `slowapi` rate limit + `X-API-Key` 인증)가 `/api/v1/query`, `/history`, `/stats`를 제공합니다.
2. `/query` 호출 시 Redis 캐시 → PostgreSQL 순으로 조회하고, 데이터가 없으면 `analysis_tasks` 큐에 작업을 제출한 뒤 최대 30초간 DB를 폴링합니다. `ecosystem` 파라미터로 npm/pip/apt 데이터를 분리하고, `force=true`일 때 해당 패키지·버전(또는 CVE)의 기존 캐시/DB 레코드를 삭제 후 재분석 작업을 제출합니다.
3. 대시보드(React/Vite)는 `axios`/React Query 기반 클라이언트로 Request ID와 API 키를 주입해 QueryAPI와 통신하고, `SearchBar/StatsCards/RecentScansTable` 조합으로 시각화합니다. `VITE_QUERY_API_BASE_URL`로 `/api/v1` 기본 경로를 설정할 수 있습니다.

---

## 3. 데이터 저장소 & 캐시

| 테이블 | 주요 필드 |
|--------|-----------|
| `package_cve_mapping` | `package`, `version_range`, `ecosystem`, `cve_ids[]` |
| `cvss_scores` / `epss_scores` | `cve_id`, 점수, `collected_at` |
| `threat_cases` | `cve_id`, `package`, `version_range`, `cases JSONB` |
| `analysis_results` | `cve_id`, `risk_level`, `risk_score`, `recommendations[]`, `analysis_summary`, `generated_at` |

Redis 네임스페이스는 `mapping:*`, `cvss:*`, `epss:*`, `threat:*`, `analysis:*`, `query:*` 등으로 구분되며 TTL(`CACHE_TTL_SECONDS`)이 적용됩니다. `AsyncCache`는 Redis 장애를 감지하면 캐시 기능을 일시 비활성화하고 폴백 모드로 전환합니다.

SQLite 초기화 스크립트(`database/init-db.sqlite.sql`)와 PostgreSQL 스크립트(`database/init-db.sql`)가 모두 제공되어 개발/테스트 환경에 맞게 사용할 수 있습니다.

---

## 4. AI 상호작용 & 보안
- **공통 인터페이스**: `common_lib/ai_clients/base.py`의 `IAIClient`를 구현하며, `tenacity` 기반 재시도 데코레이터와 httpx 타임아웃을 공유합니다.
- **PerplexityClient**: 검색 기반 JSON 응답을 받아 CVE·위협 사례를 추출합니다. API 키가 없거나 `NT_ALLOW_EXTERNAL_CALLS=false`면 RuntimeError를 던져 폴백으로 전환합니다.
- **ClaudeClient**: 위협 요약과 엔터프라이즈 리포트를 생성합니다. 번역 단계에서 기술 용어 병기 규칙을 적용합니다.
- **GPT5Client**: 권고안 및 한국어/영어 혼합 메시지를 생성합니다. 모델 이름은 `NT_GPT5_MODEL`로 변경 가능.
- **Sanitization**: ThreatAgent에서 HTML/제어문자 제거, URL 검증, 길이 제한을 수행하여 XSS/오염된 데이터 저장을 방지합니다.
- **Fallback 정책**: API 키 미설정, HTTP 오류, 타임아웃 발생 시 `_fallback_*` 함수를 통해 안전한 기본 텍스트/점수를 반환합니다.

---

## 5. 큐 & 비동기 오케스트레이션
- Redis 리스트 `analysis_tasks`에 `{package, version, force, source, ecosystem}` JSON을 push합니다.
- `worker.py`는 BLPOP으로 큐를 polling하고 `AgentOrchestrator`를 재사용하여 백그라운드 분석을 수행합니다. 처리 실패 시 페이로드·예외 메타데이터를 포함한 Dead Letter Queue(`analysis_tasks:failed`)에 적재합니다.
- QueryAPI는 `ResourceNotFound`가 발생하면 `submit_analysis_job()`으로 작업을 생성하고 `AnalysisInProgressError`(HTTP 202)를 반환합니다. 프론트엔드는 해당 상태를 배너(“보고서 생성 중...”)로 표현합니다.
- 추가적인 패키지 스캔 스케줄링은 `mapping_collector/app/scheduler.py`가 `package_scan_queue` 테이블을 poll하면서 수행합니다 (`FOR UPDATE SKIP LOCKED`로 동시성 보장).

---

## 6. 관찰성 & 회복력
- `common_lib/logger.py` + `common_lib/observability.py`가 Request ID 컨텍스트를 관리하고 JSON 로거(`python-json-logger`)를 구성합니다.
- 모든 FastAPI 엔드포인트는 Request ID 미들웨어를 통해 `X-Request-ID` 헤더를 응답에 삽입하고 slowapi rate limit 에러도 동일한 포맷을 따릅니다.
- Redis/DB 연결이 실패하면 `get_session()`과 `AsyncCache`가 경고를 남기고 폴백 모드로 자동 전환하므로 파이프라인 자체는 계속 실행됩니다.
- `scripts/health_check.py`, `scripts/verify_system.py`, `scripts/verify_fixes.py`로 서비스 상태, 인증, 캐시 동작을 자동 점검할 수 있습니다.

---

## 7. 최근 개선 사항 (2025-02-15)
1. **MappingScheduler 안정화** (`mapping_collector/app/scheduler.py`)  
   - AsyncSession을 `async for get_session()` 패턴으로 안전하게 사용하며 실패 시 rollback 및 로그를 남김.
2. **QueryAPI Force 옵션/에코시스템 격리** (`query_api/app/service.py`, `repository.py`)  
   - `force=true` 호출 시 해당 패키지·버전에 한해 캐시/DB를 삭제하고 재분석 작업을 생성하며, 모든 조회/삭제 쿼리가 `ecosystem` 파라미터로 분리되어 교차 오염을 방지.
3. **위험도 우선순위 & 통계 일관성** (`query_api/app/service.py`, `repository.py`)  
   - `risk_score` 기반의 P1/P2/P3 라벨 계산, `risk_distribution` 상의 `UNKNOWN` 대문자 정규화.
4. **ThreatAgent JSONB 직렬화 수정** (`threat_agent/app/repository.py`)  
   - `bindparam(..., type_=JSONB)`와 `pydantic_encoder`로 asyncpg `list encode` 예외 해결.
5. **Frontend Observability** (`web_frontend/src/api/client.ts`, `src/store/queryContext.tsx`)  
   - `VITE_API_URL`/`VITE_QUERY_API_URL`/`VITE_QUERY_API_BASE_URL` 지원, Request ID 생성기 폴백, axios 1.13.x 및 React 18.3.x 업그레이드.
6. **작업 큐 연동 고도화** (`worker.py`, `query_api/app/redis_ops.py`)  
   - QueryAPI가 분석 미존재 시 자동으로 큐에 작업을 넣고, 워커는 실패 시 Dead Letter Queue에 상세 메타데이터를 남깁니다.
7. **README & 검증 문서 일원화** (`README.md`, `docs/REVIEW.md`, `VERIFICATION_GUIDE.md`)  
   - 환경 변수, 회귀 테스트(`tests/test_regression.py`), 운영 체크리스트를 최신 코드와 맞춰 정리해 팀 온보딩 시간을 단축.

**Impact**: 캐시 히트율과 안정성이 향상되고, JSONB 직렬화/세션 핸들링 이슈가 제거되었으며, UI와 API 간 스키마 정렬로 사용자 경험이 개선되었습니다.

---

이 문서는 팀원과 협력사에게 시스템 구조를 설명할 때 기준 자료로 사용할 수 있습니다. 세부 API/설정/운영 절차는 `README.md`, `docs/API.md`, `docs/DOCKER.md`, `docs/REVIEW.md`, `SETUP.md`를 참고하세요.
