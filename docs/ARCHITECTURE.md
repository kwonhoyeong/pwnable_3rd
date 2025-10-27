# ARCHITECTURE

## System Overview
- 목적(Purpose): npm 패키지 공급망 공격 위협을 자동 평가하여 대응 가이드를 생성.
- 구성요소(Components): MappingCollector, CVSSFetcher, EPSSFetcher, ThreatAgent, Analyzer, QueryAPI, WebFrontend, CommonLib.
- 저장소(Storage): SQLite (로컬 파일 기반), 인메모리 캐시 (cachetools)

## High-Level Diagram
```
[Scheduler] -> MappingCollector ---> SQLite (package_cve_mapping)
                                     |
                                     v
                               CVSSFetcher --> SQLite (cvss_scores)
                                     |
                                     v
                               EPSSFetcher --> SQLite (epss_scores)
                                     |
                                     v
                                ThreatAgent --> SQLite (threat_cases)
                                     |
                                     v
                                   Analyzer --> SQLite (analysis_results)
                                     |
                                     v
                                 QueryAPI/Memory Cache --> WebFrontend
```

## Data Flow
1. MappingCollector 모듈이 npm 패키지/버전 범위 입력을 받아 관련 CVE ID 목록을 수집하고 SQLite에 저장.
2. CVSSFetcher 모듈이 CVE ID를 받아 CVSS v3 기초 점수를 조회 후 SQLite에 저장.
3. EPSSFetcher 모듈이 CVE ID를 받아 EPSS 공식 API에서 점수를 조회 후 정규화하여 SQLite에 저장.
4. ThreatAgent 모듈이 Perplexity(검색)와 Claude(요약)를 이용하여 공격 사례를 수집하고 중복 제거 후 SQLite에 저장.
5. Analyzer 모듈이 CVE, CVSS, EPSS, 사례 데이터를 결합하여 위험 등급과 대응 권고를 산출하고 SQLite에 저장.
6. QueryAPI 모듈이 SQLite와 인메모리 캐시를 활용해 통합 정보를 제공하고 위협 우선순위를 계산.
7. WebFrontend가 QueryAPI를 호출해 우선순위 기반 결과를 사용자에게 시각화.

## Database Schema Summary (SQLite)
- `package_cve_mapping(id, package, version_range, cve_ids[JSON], created_at, updated_at)`
- `cvss_scores(id, cve_id, cvss_score, severity, collected_at, created_at)`
- `epss_scores(id, cve_id, epss_score, collected_at, created_at)`
- `threat_cases(id, cve_id, package, version_range, cases[JSON], created_at, updated_at)`
- `analysis_results(id, cve_id, risk_level, recommendations[JSON], analysis_summary, generated_at, created_at)`

**Note**: ARRAY 타입은 JSON 문자열로 저장되며, SQLite의 json_each 함수를 사용하여 쿼리합니다.

## AI Responsibilities
- PerplexityClient: 웹 검색 기반 자료 수집(Web search ingestion).
- ClaudeClient: 수집한 자료 요약 및 권고 생성(Summarization & recommendation).
- GPT5Client: Analyzer에서 고급 대응 전략 생성(Advanced remediation drafting).
- 공통 AI 인터페이스(IAIClient): API 호출, 오류 재시도, 로깅 규약 공유.

## Storage Architecture
- **Database**: SQLite 파일 기반 데이터베이스 (`./data/threatdb.sqlite`)
  - 로컬 파일로 저장되어 Git 저장소에 포함 가능
  - 외부 DB 서버 불필요, Docker 설정 간소화
  - JSON1 확장 기능을 활용한 JSON 데이터 처리
- **Cache**: 인메모리 TTL 캐시 (cachetools)
  - Redis 대신 Python 프로세스 내부 캐시 사용
  - 설정 가능한 TTL (기본 3600초)
  - 프로세스 재시작 시 캐시 초기화

## Integration Notes
- 각 모듈은 독립 Docker 컨테이너로 배포 가능하며 CommonLib를 공유 라이브러리로 사용.
- SQLite 데이터베이스 파일은 bind mount를 통해 컨테이너 간 공유.
- 데이터베이스 초기화는 `scripts/init_db.py` 스크립트로 수행.
