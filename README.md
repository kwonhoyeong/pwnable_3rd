# npm 패키지 대상 CVE/EPSS 위협 평가 에이전트
## 개요(Overview)
- 목적(Purpose): npm 패키지 공급망(Supply chain) 보안 위협 탐지 및 대응 권고 자동화.
- 구성(Modules): MappingCollector, EPSSFetcher, ThreatAgent, Analyzer, QueryAPI, WebFrontend, CommonLib.
- 기술 스택(Stack): Python 3.11, FastAPI, PostgreSQL, Redis, Kafka/Redis Streams(확장), React + Vite.

## 폴더 구조(Folder structure)
```
common_lib/
  common_lib/
    ai_clients/
    config.py
    db.py
    logger.py
    cache.py
mapping_collector/
  app/
  db/
  Dockerfile
... (동일 패턴 for epss_fetcher, threat_agent, analyzer, query_api)
web_frontend/
  src/
  public/
  Dockerfile
```

## 모듈별 설명(Module descriptions)
### MappingCollector
- 역할(Role): npm 패키지 버전별 영향 CVE 매핑 수집.
- 실행(Run): `uvicorn mapping_collector.app.main:app --reload`
- 스케줄러(Scheduler): `MappingScheduler` 가 백그라운드 주기 실행.

### EPSSFetcher
- 역할(Role): CVE 기반 EPSS 점수 수집 및 저장.
- 실행(Run): `uvicorn epss_fetcher.app.main:app --reload`

### ThreatAgent
- 역할(Role): Perplexity 검색 + Claude 요약으로 공격 사례 수집.
- 실행(Run): `uvicorn threat_agent.app.main:app --reload`
- 프롬프트 템플릿(Prompt templates): `threat_agent/app/prompts.py`

### Analyzer
- 역할(Role): EPSS + 사례 기반 위험 분석 및 권고 생성.
- 실행(Run): `uvicorn analyzer.app.main:app --reload`

### QueryAPI
- 역할(Role): 통합 조회 API 제공 + Redis 캐시 활용.
- 실행(Run): `uvicorn query_api.app.main:app --reload`

### WebFrontend
- 역할(Role): React 기반 대시보드.
- 실행(Run): `npm install && npm run dev`

### CommonLib
- 역할(Role): 공통 설정/로깅/DB/AI 클라이언트 제공.

## 데이터베이스 스키마(Database schema)
- 각 모듈의 `db/schema.sql` 참고.
- 주요 테이블: `package_cve_mapping`, `epss_scores`, `threat_cases`, `analysis_results`.

## Docker 빌드/실행 예시(Docker build/run examples)
```
docker build -t mapping-collector ./mapping_collector
docker run --rm -p 8000:8000 mapping-collector
```
(다른 모듈도 동일 패턴 적용)

## 메시징/이벤트(Messaging/Event)
- Kafka 또는 Redis Streams 연동 포인트: 각 서비스의 확장 포인트에 적용 예정(To be integrated).

## 개발 가이드(Development guide)
1. `.env` 파일에 API 키 및 DSN 설정.
2. `poetry` 또는 `pip` 로 공통 의존성 설치.
3. 테스트(Test) 및 린트(Lint) 도구는 추후 정의 예정.

## Prompt 템플릿 예시(Prompt examples)
- ThreatAgent Perplexity: `SEARCH_PROMPT_TEMPLATE`.
- ThreatAgent Claude: `SUMMARY_PROMPT_TEMPLATE`.

