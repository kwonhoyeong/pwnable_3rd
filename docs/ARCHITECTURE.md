# ARCHITECTURE

## System Overview
- **목적(Purpose)**: npm 패키지 공급망 공격 위협을 자동 평가하여 대응 가이드를 생성
- **구성요소(Components)**: MappingCollector, CVSSFetcher, EPSSFetcher, ThreatAgent, Analyzer, QueryAPI, WebFrontend, CommonLib
- **아키텍처 패턴**: Event-driven pipeline with caching and persistence layers

## High-Level Diagram
```
                    ┌────────────────────────┐
                    │  AgentOrchestrator     │
                    │  (Pipeline Manager)    │
                    └────────────┬───────────┘
                                 │progress events
                                 ▼
                        ┌─────────────────┐
                        │  MappingAgent   │◄────► Redis (CVE cache)
                        └────────┬────────┘
                                 │CVE IDs ┌──────────────┐
                                 ├────────►│ PostgreSQL  │
              ┌──────────────────┴─────────┤   Mapping   │
              │                            └──────────────┘
              │  (parallel execution)
              ▼                                     ▼
      ┌───────────────┐                     ┌───────────────┐
      │   CVSSAgent   │◄────► Redis cache   │   EPSSAgent   │◄────► Redis cache
      └───────┬───────┘                     └───────┬───────┘
              │                                     │
              │  ┌──────────────┐                  │
              └──►│ PostgreSQL  │◄─────────────────┘
                  │ CVSS/EPSS   │
                  └──────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │ ThreatAgent  │◄────► Redis cache (per CVE)
                  │ (Sanitized)  │
                  └──────┬───────┘
                         │cases  ┌──────────────┐
                         ├───────►│ PostgreSQL  │
                         │        │ ThreatCases │
                         │        └──────────────┘
                         ▼
                  ┌──────────────┐
                  │ AnalyzerAgent│◄────► Redis cache (analysis)
                  └──────┬───────┘
                         │reports ┌──────────────┐
                         └────────►│ PostgreSQL  │
                                   │  Analysis   │
                                   └──────┬───────┘
                                          │
                                          ▼
                                   QueryAPI/WebFrontend
```

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
- AI 기반 대응 전략 생성
- **DB 저장**: `AnalysisRepository.upsert_analysis()`로 분석 결과 저장
- **캐시 저장**: 향후 동일 요청 시 재사용

### 6. Data Serving
- `QueryAPI`/`WebFrontend`가 PostgreSQL과 Redis를 조회하여 사용자에게 결과 노출
- 우선순위 기반 정렬 (CVSS, EPSS 점수 기반)

## Database Schema Summary
- `package_cve_mapping(id, package, version_range, cve_ids, created_at, updated_at)`
- `cvss_scores(id, cve_id, cvss_score, vector, collected_at, created_at)`
- `epss_scores(id, cve_id, epss_score, collected_at)`
- `threat_cases(id, cve_id, package, source, title, summary, collected_at)`
- `analysis_results(id, cve_id, risk_level, recommendations, analysis_summary, generated_at, created_at)`
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

### Impact
- **성능**: 캐시 히트율 향상, 불필요한 API 호출 감소
- **안정성**: 리소스 누수 해결, 동시성 이슈 제거
- **보안**: XSS 방지, 입력 검증 강화
- **데이터 무결성**: DB 저장 보장, 큐 처리 정확도 향상
