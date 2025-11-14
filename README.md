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
1. `python3 -m venv .venv && source .venv/bin/activate`
2. `python3 -m pip install -r requirements.txt`
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
3. 가상환경을 활성화한 상태에서 `python3 main.py --package lodash` 명령을 실행하면 파이프라인이 동작합니다.

## Quick Start
```bash
# 가장 빠르게 전체 시스템 실행하는 방법
python3 main.py --package lodash
```

## Helper Script (`run_pipeline.sh`)
```bash
# 최초 실행 시 의존성 설치까지 수행(Install deps on first run)
bash run_pipeline.sh --package lodash --install-deps

# ThreatAgent 단계를 생략하고 실행(Skip threat collector)
bash run_pipeline.sh --package lodash --skip-threat-agent

# 실행 전 실행 권한을 부여할 수도 있습니다(optional chmod)
chmod +x run_pipeline.sh
./run_pipeline.sh --package lodash
```
> `.env` 파일이 준비되어 있어야 하며(PostgreSQL/Redis), 필요한 경우 `--python`으로 다른 인터프리터를 지정할 수 있습니다.

## Pipeline at a Glance
1. `AgentOrchestrator` → 각 에이전트의 실행 순서를 정의하고 진행 상황을 브로드캐스트합니다.
2. MappingAgent → 패키지/버전 입력에 대한 CVE를 캐시 조회 후 수집합니다.
3. CVSSAgent & EPSSAgent → `asyncio.gather`로 동시에 실행되며 점수를 조회하고 캐싱합니다.
4. ThreatAgent → 필요 시 위협 사례를 모으고, `--skip-threat-agent` 옵션 시 안전한 기본값으로 대체합니다.
5. AnalyzerAgent → 위협·점수 데이터를 통합해 위험 등급/권고를 생성하고 캐시로 재사용합니다.
6. QueryAPI/WebFrontend → Redis 캐시로 가속된 통합 결과를 사용자에게 노출합니다.

## Documentation
- 더 자세한 내용은 `docs/ARCHITECTURE.md`, `docs/API.md` 참고

## License
- MIT License
