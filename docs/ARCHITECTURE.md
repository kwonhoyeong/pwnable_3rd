# ARCHITECTURE

## System Overview
- **목적(Purpose)**: npm 패키지 공급망 공격 위협을 자동 평가하여 대응 가이드를 생성
- **구성요소(Components)**: MappingCollector, CVSSFetcher, EPSSFetcher, ThreatAgent, Analyzer, QueryAPI, WebFrontend, CommonLib
- **아키텍처 패턴**: Event-driven pipeline with caching and persistence layers

## High-Level Diagram
<img width="725" height="1183" alt="이름 없는 노트북" src="https://github.com/user-attachments/assets/be8b85c0-a7eb-4d77-a20b-f9a49886c315" />


## Data Flow

### 1. Pipeline Initialization
- `AgentOrchestrator`가 DB 세션(`get_session`)을 생성하고 각 리포지토리(MappingRepository, CVSSRepository, EPSSRepository, ThreatRepository, AnalysisRepository)를 초기화
- `--force` 플래그가 있으면 캐시를 무시하고 강제 갱신

### 2. Mapping Stage (CVE Collection)
- `MappingAgent`가 npm 패키지 입력을 받아 CVE 목록을 수집
- **캐시 조회**: `if cached is not None` 체크로 빈 결과(`[]`)도 유효한 캐시 히트로 처리
- **DB 저장**: `MappingRepository.upsert_mapping()`으로 PostgreSQL에 패키지-CVE 매핑 저장
- **캐시 저장**: Redis에 결과 저장 (TTL 적용)

### 3. Score Collection Stage (Parallel Execution)
- `CVSSAgent`와 `EPSSAgent`가 `asyncio.gather`로 병렬 실행
- 각 CVE에 대해 CVSS/EPSS 점수 수집
- **캐시 조회**: 빈 딕셔너리(`{}`)도 유효한 캐시 히트로 처리
- **DB 저장**: 각각 `CVSSRepository.upsert_score()`, `EPSSRepository.upsert_score()`로 저장
- **Fallback 처리**: 실패 시 기본값 사용 (CVSS: 5.0, EPSS: 0.5)

### 4. Threat Intelligence Stage
- `ThreatAgent`가 각 CVE에 대해 위협 사례 수집
- **출력 Sanitization**: HTML/제어 문자 제거, URL 검증, 길이 제한으로 XSS 방지
- **캐시 조회**: 이전 결과 재사용
- **DB 저장**: `ThreatRepository.upsert_cases()`로 sanitize된 사례 저장
- **Skip 옵션**: `--skip-threat-agent` 플래그 시 안전한 기본값 반환

### 5. Analysis Stage
- `AnalyzerAgent`가 CVSS/EPSS 점수와 위협 사례를 종합하여 위험도 평가
- Claude 시스템 프롬프트(시니어 AppSec 엔지니어 역할)로 Markdown 리포트, GPT5로 권고안 생성
- **가중치 기반 스코어링**: `risk_score = CVSS*0.4 + (EPSS*10)*0.3 + AI_SCORE*0.3` (AI score는 CRITICAL/HIGH/MEDIUM/LOW → 9.5/7.5/5/2)
- **DB 저장**: `AnalysisRepository.upsert_analysis()`로 `risk_level`, `risk_score`, `recommendations`, `analysis_summary` 영구 저장
- **캐시 저장**: 향후 동일 요청 시 재사용

### 6. Data Serving
- `QueryAPI`가 FastAPI 0.121 기반으로 `/api/v1/query`, `/api/v1/history`, `/api/v1/stats`를 제공
  - Request ID 미들웨어가 모든 응답 헤더/로그에 `X-Request-ID`를 삽입
  - `/query`는 패키지/CVE별 데이터를 Redis 캐시+DB로부터 불러오고, 대소문자 무관한 위험도 우선순위를 계산
  - `/history`는 최신 `analysis_results` 기준 페이지네이션, `/stats`는 위험도 카운트를 집계
- React/Vite 프런트엔드는 `SearchBar`, `StatsCards`, `RiskDistributionChart`, `RecentScansTable` 컴포넌트를 조합해 대시보드를 구성

## Database Schema Summary
- `package_cve_mapping(id, package, version_range, cve_ids, created_at, updated_at)`
- `cvss_scores(id, cve_id, cvss_score, vector, collected_at, created_at)`
- `epss_scores(id, cve_id, epss_score, collected_at)`
- `threat_cases(id, cve_id, package, source, title, summary, collected_at)`
- `analysis_results(id, cve_id, risk_level, risk_score, recommendations, analysis_summary, generated_at, created_at)`
- Redis는 `mapping:*`, `epss:*`, `cvss:*`, `threat:*`, `analysis:*` 네임스페이스를 통해 캐시 TTL(`CACHE_TTL_SECONDS`)이 적용된 결과를 저장한다.

## AI Responsibilities

### AI Clients Architecture
- **공통 인터페이스**: `IAIClient` - API 호출, 오류 재시도, 로깅 규약 공유
- **리소스 관리**: 각 요청마다 단기 `httpx.AsyncClient` 인스턴스 생성/종료로 연결 누수 방지
- **타임아웃 설정**: 모든 AI 호출에 configurable timeout 적용

### AI Client Roles
1. **PerplexityClient**
   - 웹 검색 기반 자료 수집 (Web search ingestion)
   - 실시간 위협 정보 검색

2. **ClaudeClient**
   - 수집한 자료 요약 및 권고 생성 (Summarization & recommendation)
   - 위협 사례 요약문 생성

3. **GPT5Client**
   - Analyzer에서 고급 대응 전략 생성 (Advanced remediation drafting)
   - 종합 위험 평가 및 권장 사항 도출

### Security Measures
- **출력 Sanitization**: AI 응답에서 HTML 태그, 제어 문자 제거
- **URL 검증**: AI가 생성한 URL의 유효성 검증
- **길이 제한**: 과도하게 긴 응답 방지
- **XSS 방지**: 사용자 입력 및 AI 출력 이스케이프 처리

## Queue Processing (MappingCollector)
- **동시성 제어**: `FOR UPDATE SKIP LOCKED`로 여러 워커 간 충돌 방지
- **버전 관리**: `version_range` 필드를 큐에서 읽어 정확한 버전 범위 처리
- **상태 관리**: 처리 완료 후 `processed=true` 플래그 설정
- **재처리 방지**: 처리된 항목은 재조회되지 않음

## Integration Notes
- **이벤트 버스**: Kafka/Redis Streams는 Collector→Analyzer 간 데이터 전달 확장 시 사용
- **모듈화**: 각 모듈은 독립 Docker 컨테이너로 배포 가능
- **공유 라이브러리**: CommonLib를 통해 DB, 캐시, 로깅, AI 클라이언트 공유
- **트랜잭션 관리**: SQLAlchemy async session으로 각 단계별 DB 커밋
- **캐싱 전략**: Redis TTL 기반 캐시로 외부 API 호출 최소화
- **에러 핸들링**: Fallback 메커니즘으로 부분 실패 시에도 파이프라인 진행

## Recent Improvements (2025-11)

### High Priority Fixes
1. **DB Persistence Layer** (`agent_orchestrator.py:137-216`)
   - 각 파이프라인 단계별로 PostgreSQL에 데이터 저장
   - Repository 패턴을 통한 DB 접근 통일
   - QueryAPI/WebFrontend가 실제 데이터를 조회할 수 있도록 개선

2. **Queue Processing Enhancement** (`mapping_collector/app/`)
   - `FOR UPDATE SKIP LOCKED`를 사용한 동시성 제어
   - `version_range` 필드를 큐에서 올바르게 읽어 처리
   - 처리 완료 후 `processed=true` 플래그 설정으로 무한 재처리 방지

3. **Resource Leak Prevention** (`common_lib/ai_clients/`)
   - AI 클라이언트의 HTTP 연결 누수 수정
   - 각 요청마다 단기 `httpx.AsyncClient` 생성/종료
   - File descriptor 고갈 문제 해결

### Medium Priority Fixes
4. **Cache Logic Improvement** (`agent_orchestrator.py:272,299,327,364,395`)
   - `if cached is not None` 체크로 빈 결과도 유효한 캐시 히트로 처리
   - CVE가 없는 패키지나 점수가 없는 경우 불필요한 재요청 방지
   - Rate limit 절약

5. **Security Enhancement** (`threat_agent/app/services.py:16-134`)
   - AI 출력에 대한 포괄적인 sanitization 추가
   - HTML/제어 문자 제거, URL 검증, 길이 제한
   - XSS 공격 벡터 차단

### Latest Fixes (2025-02-15)
6. **Mapping Scheduler Stability** (`mapping_collector/app/scheduler.py`)
   - AsyncSession을 `async for get_session()` 패턴으로 안전하게 획득
   - 트랜잭션 실패 시 rollback + 에러 로깅 추가

7. **Prioritization Accuracy** (`query_api/app/service.py`)
   - 위험도 문자열을 대문자로 정규화하여 `CRITICAL/HIGH`도 올바른 가중치를 적용
   - 대시보드의 P1/P2/P3 레이블이 분석 결과와 일치

8. **Frontend Observability** (`web_frontend/src/api/client.ts`)
   - `VITE_API_URL`/`VITE_QUERY_API_URL` 환경 변수 지원, Request ID 생성기 폴백 추가
   - axios 1.13.x + React 18.3.x로 업그레이드

### Impact
- **성능**: 캐시 히트율 향상, 불필요한 API 호출 감소
- **안정성**: 리소스 누수 해결, 동시성 이슈 제거
- **보안**: XSS 방지, 입력 검증 강화
- **데이터 무결성**: DB 저장 보장, 큐 처리 정확도 향상
- **코드 품질**: 중복 제거, 명확한 에러 메시지, 유지보수성 향상
