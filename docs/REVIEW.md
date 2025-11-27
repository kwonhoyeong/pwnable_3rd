# 개발 현황 & 코드 리뷰 리포트

---

## 1. 개발 현황 브리핑
- **파이프라인 완성**: `agent_orchestrator.py:112-420`와 `worker.py:1-120`가 MappingCollector → CVSS/EPSS Fetcher → ThreatAgent → Analyzer → QueryAPI/Web UI까지 전 단계를 orchestration/작업 큐로 묶어 실행합니다. Redis 캐시와 PostgreSQL 영속화, AI 폴백까지 모두 연결된 상태입니다.
- **데이터 수집 체계 구축**: `mapping_collector/app/service.py`, `cvss_fetcher/app/service.py`, `epss_fetcher/app/service.py`가 Perplexity + 외부 공식 API(NVD/FIRST.org) 조합으로 CVE/점수를 수집하며, 실패 시 폴백 데이터와 Redis 캐시/DB upsert까지 처리합니다.
- **Threat & Analyzer AI 파이프라인**: `threat_agent/app/services.py`는 Perplexity 검색 → Claude 요약 → Sanitization을 수행하고 JSONB 저장까지 마무리합니다. `analyzer/app/service.py`는 Claude 기반 Markdown 리포트, GPT-5 권고안, 가중치 `risk_score` 계산, 한국어 번역까지 제공합니다.
- **QueryAPI/대시보드 구현**: `query_api/app/main.py`는 FastAPI + slowapi Rate limit + X-API-Key 인증을 제공하며, 데이터 미존재 시 Redis에 분석 작업을 제출하고 `ANALYSIS_IN_PROGRESS`를 응답합니다. `web_frontend/src/pages/DashboardPage.tsx`는 React Query 기반 UI에서 검색/통계/최근 분석을 시각화하고 Request ID 헤더를 자동 주입합니다.
- **공통 인프라 & 문서화**: `common_lib/` 하위에 설정, 로깅, Redis 캐시, DB 세션, AI 클라이언트, 재시도 유틸이 정리되어 있습니다. `docs/*.md`, `scripts/`, `demo/` 폴더에 설치·헬스체크·검증 스크립트, JSONB 수정 내역 등이 포함되어 온보딩과 운영에 활용 가능합니다.

---

## 2. 백엔드 리뷰

### 2.1 파이프라인 & 오케스트레이션
- `agent_orchestrator.py:112-420`
  - **장점**: 단계별 캐시 키 전략, `_safe_call`을 통한 재시도+폴백, DB 세션 사용 여부에 따른 upsert 처리, Threat/Analyzer 캐시 재사용 로직이 명확합니다.
  - **검토 포인트**: 현재 Redis/DB 비활성 시 로그만 남기고 진행하는데, 운영 환경에서는 장애 탐지/알람 연계 필요. 또한 Threat/Analyzer 캐시 TTL이 전역 `CACHE_TTL_SECONDS`를 그대로 따르므로 AI 응답 최신성이 필요한 경우 서비스별 TTL 튜닝 고려.
- `worker.py`
  - Redis BLPOP 루프와 graceful shutdown 이벤트가 구현되어 있음. 작업 JSON 검증이 최소화되어 있으므로, production에서는 필드 스키마 검증/metrics 추가 권장.

### 2.2 데이터 수집 계층
- `mapping_collector/app/service.py`
  - Perplexity → 공식 Feed 순으로 조회하며 `normalize_cve_ids`로 정규화합니다. HTTP 타임아웃과 예외 처리가 세분화되어 폴백 동작이 일관적입니다.
  - 이미 `MappingScheduler`가 `async for get_session()` 패턴으로 수정되어 `async_generator` 경고 해결, 트랜잭션 롤백 및 로그도 보강되었습니다.
- `cvss_fetcher/app/service.py`, `epss_fetcher/app/service.py`
  - httpx + asyncio.wait_for로 타임아웃 제어, 재시도(loop) 포함.
  - **주의**: NVD/EPSS API rate limit 대비 sleep(0.1s) 정도만 있어 burst 상황에서 제한에 걸릴 수 있으므로 환경 변수 기반 rate control 추가를 검토해도 좋습니다.
  - Repository(`cvss_fetcher/app/repository.py`, `epss_fetcher/app/repository.py`)는 단순 upsert이며 문제 없음.

### 2.3 ThreatAgent & Analyzer
- `threat_agent/app/services.py`
  - `_sanitize_text`, `_sanitize_source`, `_serialize_threat_case` 등으로 AI 응답을 정제하여 XSS/제어문자를 차단합니다.
  - JSON 파싱 실패 시 수동 파싱으로도 제목/요약을 추출하고, URL 검증 실패 시 안전한 기본값 사용.
  - JSONB 저장(`threat_agent/app/repository.py`)은 `bindparam("cases", type_=JSONB)`와 `pydantic_encoder`로 직렬화 이슈를 해결했습니다 (`docs/JSONB_FIX_EXPLANATION.md` 참고).
- `analyzer/app/service.py`
  - Claude Enterprise 리포트 + GPT-5 권고안 + 가중치 스코어링을 동시에 수행합니다.
  - `EnterpriseAnalysisGenerator._translate_to_korean`에서 규칙 기반 번역 지침을 둬 결과 일관성을 확보했습니다.
  - **확인 사항**: `RecommendationGenerator`와 Claude 호출 모두 외부 API 키 없이 실행 시 RuntimeError를 던져 폴백으로 전환하는 구조이므로, 운영 로그에서 키 미설정이 계속 관측되면 `.env` 관리 프로세스 강화 필요.

### 2.4 QueryAPI & Redis 큐 연동
- `query_api/app/main.py`
  - Request ID 미들웨어, slowapi rate limiting, AppException 핸들러, 인증(`X-API-Key`), CORS 설정이 완료되어 있습니다.
  - `/api/v1/query`는 패키지/버전/CVE 파라미터에 맞춰 DB 조회 후 캐시 저장, 발견되지 않으면 `submit_analysis_job`으로 워커를 트리거하고 최대 30초 폴링 제공합니다.
- `query_api/app/service.py`
  - `force=true` 호출 시 Redis/DB 캐시를 우회하고 해당 패키지·버전 혹은 CVE의 기존 레코드를 삭제한 뒤 재분석 작업을 생성합니다. `ecosystem` 파라미터가 모든 조회·삭제 경로에 전달되어 서로 다른 레지스트리 데이터가 섞이지 않습니다.
  - 패키지/CVE 파라미터가 모두 비어 있으면 `InvalidInputError`로 400을 반환하며, `AnalysisInProgressError`(HTTP 202)로 진행 중 상태를 명확히 전달합니다.
- `query_api/app/repository.py`
  - SQL 텍스트 + 파라미터 바인딩으로 안전하게 집계를 수행하고, 위험 통계는 `CRITICAL/HIGH/.../UNKNOWN` 대문자 키만 노출합니다.
- `query_api/app/redis_ops.py`
  - Redis 클라이언트가 lazy-init되고 RPUSH/LLEN을 비동기로 처리합니다. 오류 시 경고 로그 후 false를 반환하도록 되어 있어 운영 측면에서 메트릭 보강 필요.

---

## 3. 프론트엔드 리뷰
- `web_frontend/src/api/client.ts`
  - Axios 인터셉터에서 `X-Request-ID`를 생성·세션 저장하고, `VITE_QUERY_API_KEY`를 자동 첨부합니다. `VITE_API_URL`/`VITE_QUERY_API_URL` 우선순위가 명시되어 배포 환경 설정이 명확합니다.
- `web_frontend/src/pages/DashboardPage.tsx`
  - React Query를 사용하며 Stats/History/Search를 각각 캐시합니다. 에러 코드(`ANALYSIS_IN_PROGRESS`, `RESOURCE_NOT_FOUND`, 등)를 `getErrorCode`/`getErrorMessage`로 구분해 UI 피드백을 제공합니다.
  - 사용자 입력 버전을 그대로 QueryAPI에 전달하도록 수정되어, 백엔드와 스키마가 일치합니다.
- `components/dashboard/*`
  - `RecentScansTable`가 `risk_score` null 케이스를 가드 처리하며, `StatsCards`는 risk distribution 데이터를 바로 시각화합니다.
- 빌드 구성: Vite dev 서버(`/api` proxy), Tailwind tokens, React Query Devtools 등 개발 편의 기능이 준비되어 있습니다.

---

## 4. 공통 인프라 & 문서화
- `common_lib/config.py`, `cache.py`, `db.py`, `ai_clients/*`, `retry_config.py`가 설정/캐시/DB/AI/재시도 로직을 표준화합니다.
  - `AsyncCache`는 Redis 장애를 감지하면 `_disabled` 플래그로 폴백하는데, 재활성화는 프로세스 재기동 시 이루어집니다.
  - `get_session()`은 DB 비활성화 시 `None`을 yield하여 오케스트레이터/QueryAPI가 인메모리 폴백을 사용하도록 설계돼 있습니다.
- 문서 & 스크립트:
  - `README.md`에 전체 기능/설정/실행 절차/제한 사항/최근 개선 사항이 정리되어 팀원 onboarding에 활용 가능합니다.
  - `SETUP.md`, `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/DOCKER.md`, `docs/JSONB_FIX_EXPLANATION.md` 등 상세 문서와 `scripts/*.py`, `demo/`가 제공됩니다.
  - 회귀/수동 검증 절차는 `VERIFICATION_GUIDE.md`와 `tests/test_regression.py`에 정리되어 있어 배포 전 체크리스트로 활용할 수 있습니다.

---

## 5. 리스크 & 다음 단계 제안
1. **운영 모니터링**: Redis/DB/AI 키 미구성 시 로그에만 남으므로, 통합 모니터링(예: Prometheus metrics, alert) 추가 검토.
2. **Rate Limit 관리**: 외부 API(NVD/FIRST.org, GPT-5/Claude) 호출 빈도를 환경 변수로 제어하거나 중앙 throttling을 도입하면 안정성이 향상됩니다.
3. **에러 피드백 강화**: QueryAPI가 `ANALYSIS_IN_PROGRESS`를 반환한 뒤에도 오래 대기하면 사용자 경험이 떨어질 수 있으니, 워커 진행 상황을 폴링/웹소켓으로 노출하는 방안 고려.
4. **보안 정비**: Docker Compose는 개발용이므로, 프로덕션에서는 비밀관리, 비-루트 사용자, 네트워크 정책, HTTPS 프록시 구성 등을 추가해야 합니다.
5. **테스트 커버리지**: `tests/test_regression.py`로 인증·Stats·CVSS Fetcher·멀티 에코시스템 시나리오를 빠르게 검증할 수 있으나, 통합 테스트(예: orchestrator happy path, QueryAPI endpoints E2E)까지 확대하면 안정성이 더욱 높아집니다.
