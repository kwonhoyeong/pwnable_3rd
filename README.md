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

## 빠른 테스트(Quick main test)
다음 커맨드는 각 모듈의 엔드포인트를 빠르게 확인할 수 있는 `python -m ...main` 실행 예시입니다.

```bash
# 1) 공통 의존성 설치 후 .env 준비
pip install -r requirements.txt

# 2) 개별 서비스 기동
python -m uvicorn mapping_collector.app.main:app --reload --port 8000
python -m uvicorn epss_fetcher.app.main:app --reload --port 8001
python -m uvicorn threat_agent.app.main:app --reload --port 8002
python -m uvicorn analyzer.app.main:app --reload --port 8003
python -m uvicorn query_api.app.main:app --reload --port 8004

# 3) 프런트엔드에서 통합 확인 (별도 터미널)
cd web_frontend && npm install && npm run dev
```

서비스 실행 후에는 `curl http://127.0.0.1:8004/api/v1/query?package=lodash` 로 end-to-end 연동을 점검할 수 있습니다.

## 모듈별 설명(Module descriptions)
각 디렉토리별 README에서 상세 실행/테스트 방법을 제공합니다.

### MappingCollector
- 역할(Role): npm 패키지 버전별 영향 CVE 매핑 수집.
- 상세 설명(Details): `mapping_collector/README.md` 참고.

### EPSSFetcher
- 역할(Role): CVE 기반 EPSS 점수 수집 및 저장.
- 상세 설명(Details): `epss_fetcher/README.md` 참고.

### ThreatAgent
- 역할(Role): Perplexity 검색 + Claude 요약으로 공격 사례 수집.
- 상세 설명(Details): `threat_agent/README.md` 참고.

### Analyzer
- 역할(Role): EPSS + 사례 기반 위험 분석 및 권고 생성.
- 상세 설명(Details): `analyzer/README.md` 참고.

### QueryAPI
- 역할(Role): 통합 조회 API 제공 + Redis 캐시 활용.
- 상세 설명(Details): `query_api/README.md` 참고.

### WebFrontend
- 역할(Role): React 기반 대시보드.
- 상세 설명(Details): `web_frontend/README.md` 참고.

### CommonLib
- 역할(Role): 공통 설정/로깅/DB/AI 클라이언트 제공.
- 상세 설명(Details): `common_lib/README.md` 참고.

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

