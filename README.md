# npm 공급망 CVE/EPSS 대응 파이프라인 (NPM Supply Chain CVE/EPSS Response Pipeline)

## Repository Layout
```
  ├── main.py
  ├── common_lib/
  ├── mapping_collector/
  ├── cvss_fetcher/
  ├── epss_fetcher/
  ├── threat_agent/
  ├── analyzer/
  ├── query_api/
  ├── web_frontend/
  ├── demo/
  └── .env.example
```

## Requirements
- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Node.js 18+ (WebFrontend)

## Setup
1. `python -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `cp .env.example .env` 후 AI API 키와 데이터베이스/캐시 DSN을 설정
4. (선택 사항) `npm install` inside `web_frontend/`

## Run main.py locally
1. PostgreSQL과 Redis를 실행하세요(Start PostgreSQL & Redis).
   - PostgreSQL에서 `threatdb` 데이터베이스를 만든 후 각 모듈의 `db/schema.sql`을 순서대로 실행합니다(`psql -f mapping_collector/db/schema.sql` 등).
   - Redis는 기본 포트(6379)로 실행하면 됩니다.
2. `.env` 파일에 아래와 같이 접속 정보를 채웁니다(Fill in connection details).
   ```dotenv
   NT_POSTGRES_DSN=postgresql+asyncpg://<user>:<password>@localhost:5432/threatdb
   NT_REDIS_URL=redis://localhost:6379/0
   ```
3. 가상환경을 활성화한 상태에서 `python main.py --package lodash` 명령을 실행하면 파이프라인이 동작합니다.

## Quick Start
```bash
# 가장 빠르게 전체 시스템 실행하는 방법
python main.py --package lodash
```

## Pipeline at a Glance
1. MappingCollector → CVE 수집(Collect CVEs)
2. CVSSFetcher → CVSS 기초 점수 수집(Get CVSS base scores)
3. EPSSFetcher → 위험 점수 조회(Get EPSS scores)
4. ThreatAgent → 공격 사례 탐색 및 요약(Search & summarize threat cases)
5. Analyzer → 위험 등급/권고 산출(Calculate risk & advice)
6. QueryAPI/WebFrontend → 우선순위 결과 제공(Present prioritized results)

## Documentation
- 더 자세한 내용은 `docs/ARCHITECTURE.md`, `docs/API.md` 참고

## License
- MIT License
