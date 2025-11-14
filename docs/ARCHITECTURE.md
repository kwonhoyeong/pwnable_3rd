# ARCHITECTURE

## System Overview
- 목적(Purpose): npm 패키지 공급망 공격 위협을 자동 평가하여 대응 가이드를 생성.
- 구성요소(Components): MappingCollector, CVSSFetcher, EPSSFetcher, ThreatAgent, Analyzer, QueryAPI, WebFrontend, CommonLib.

## High-Level Diagram
```
                    ┌────────────────────────┐
                    │    AgentOrchestrator   │
                    └────────────┬───────────┘
                                 │progress events
                                 ▼
                        ┌─────────────────┐
                        │  MappingAgent   │◄────► Redis (CVE cache)
                        └────────┬────────┘
                                 │CVE IDs
                    ┌────────────┴────────────────────────┐
                    │                                     │
                    ▼                                     ▼
            ┌───────────────┐                     ┌───────────────┐
            │   CVSSAgent   │◄────► Redis cache   │   EPSSAgent   │◄────► Redis cache
            └───────────────┘                     └───────────────┘
                    │                                     │
                    └──────────────┬──────────────────────┘
                                   ▼
                            ┌──────────────┐
                            │ ThreatAgent  │◄────► Redis cache (per CVE)
                            └──────────────┘
                                   │cases
                                   ▼
                            ┌──────────────┐
                            │ AnalyzerAgent│◄────► Redis cache (analysis)
                            └──────────────┘
                                   │reports
                                   ▼
                            PostgreSQL/QueryAPI/Web
```

## Data Flow
1. AgentOrchestrator가 Mapping/CVSS/EPSS/Threat/Analyzer 에이전트를 순서대로 또는 병렬(`asyncio.gather`)로 호출한다.
2. 각 에이전트는 실행 전에 Redis 기반 `AsyncCache`를 조회하여 기존 결과가 있으면 즉시 재사용한다.
3. MappingAgent가 npm 패키지 입력을 받아 CVE 목록을 수집하고 캐시에 저장한다.
4. CVSSAgent와 EPSSAgent가 동일한 CVE 집합을 동시에 조회하며, 실패 시 기존 fallback 로직을 호출한다.
5. ThreatAgent가 검색/요약 기반 위협 사례를 가져오고, `--skip-threat-agent` 옵션이면 안전한 기본값을 반환한다.
6. AnalyzerAgent가 점수 및 사례를 묶어 위험 등급과 대응 전략을 계산한 뒤 Redis에 캐시하고, 필요 시 PostgreSQL/QueryAPI로 전파한다.
7. QueryAPI/WebFrontend는 캐시된 데이터를 활용해 사용자에게 우선순위 기반 결과를 노출한다.

## Database Schema Summary
- `package_cve_mapping(id, package, version_range, cve_ids, created_at, updated_at)`
- `cvss_scores(id, cve_id, cvss_score, vector, collected_at, created_at)`
- `epss_scores(id, cve_id, epss_score, collected_at)`
- `threat_cases(id, cve_id, package, source, title, summary, collected_at)`
- `analysis_results(id, cve_id, risk_level, recommendations, analysis_summary, generated_at, created_at)`
- Redis는 `mapping:*`, `epss:*`, `cvss:*`, `threat:*`, `analysis:*` 네임스페이스를 통해 캐시 TTL(`CACHE_TTL_SECONDS`)이 적용된 결과를 저장한다.

## AI Responsibilities
- PerplexityClient: 웹 검색 기반 자료 수집(Web search ingestion).
- ClaudeClient: 수집한 자료 요약 및 권고 생성(Summarization & recommendation).
- GPT5Client: Analyzer에서 고급 대응 전략 생성(Advanced remediation drafting).
- 공통 AI 인터페이스(IAIClient): API 호출, 오류 재시도, 로깅 규약 공유.

## Integration Notes
- Kafka/Redis Streams 이벤트 버스는 Collector→Analyzer 간 데이터 전달을 확장할 때 사용.
- 각 모듈은 독립 Docker 컨테이너로 배포 가능하며 CommonLib를 공유 라이브러리로 사용.
