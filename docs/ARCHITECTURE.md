# ARCHITECTURE

## System Overview
- 목적(Purpose): npm 패키지 공급망 공격 위협을 자동 평가하여 대응 가이드를 생성.
- 구성요소(Components): MappingCollector, EPSSFetcher, ThreatAgent, Analyzer, QueryAPI, WebFrontend, CommonLib.

## High-Level Diagram
```
[Scheduler] -> MappingCollector ---> PostgreSQL (package_cve_mapping)
                                     |
                                     v
                               EPSSFetcher --> PostgreSQL (epss_scores)
                                     |
                                     v
                                ThreatAgent --> PostgreSQL (threat_cases)
                                     |
                                     v
                                   Analyzer --> PostgreSQL (analysis_results)
                                     |
                                     v
                                 QueryAPI/Redis Cache --> WebFrontend
```

## Data Flow
1. MappingCollector 모듈이 npm 패키지/버전 범위 입력을 받아 관련 CVE ID 목록을 수집하고 저장.
2. EPSSFetcher 모듈이 CVE ID를 받아 EPSS 공식 API에서 점수를 조회 후 정규화하여 저장.
3. ThreatAgent 모듈이 Perplexity(검색)와 Claude(요약)를 이용하여 공격 사례를 수집하고 중복 제거 후 저장.
4. Analyzer 모듈이 CVE, EPSS, 사례 데이터를 결합하여 위험 등급과 대응 권고를 산출.
5. QueryAPI 모듈이 PostgreSQL과 Redis 캐시를 활용해 통합 정보를 제공.
6. WebFrontend가 QueryAPI를 호출해 결과를 사용자에게 시각화.

## Database Schema Summary
- `package_cve_mapping(id, package, version_range, cve_id, collected_at)`
- `epss_scores(id, cve_id, epss_score, percentile, collected_at)`
- `threat_cases(id, cve_id, package, source, title, summary, collected_at)`
- `analysis_results(id, cve_id, package, risk_level, recommendations, analysis_summary, generated_at)`

## AI Responsibilities
- PerplexityClient: 웹 검색 기반 자료 수집(Web search ingestion).
- ClaudeClient: 수집한 자료 요약 및 권고 생성(Summarization & recommendation).
- GPT5Client: Analyzer에서 고급 대응 전략 생성(Advanced remediation drafting).
- 공통 AI 인터페이스(IAIClient): API 호출, 오류 재시도, 로깅 규약 공유.

## Integration Notes
- Kafka/Redis Streams 이벤트 버스는 Collector→Analyzer 간 데이터 전달을 확장할 때 사용.
- 각 모듈은 독립 Docker 컨테이너로 배포 가능하며 CommonLib를 공유 라이브러리로 사용.
