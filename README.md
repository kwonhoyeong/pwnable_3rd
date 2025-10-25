# npm 공급망 CVE/EPSS 대응 파이프라인 (NPM Supply Chain CVE/EPSS Response Pipeline)

## Repository Layout
```
  ├── main.py
  ├── common_lib/
  ├── mapping_collector/
  ├── epss_fetcher/
  ├── threat_agent/
  ├── analyzer/
  ├── query_api/
  ├── web_frontend/
  └── .env
```

## Requirements
- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Node.js 18+ (WebFrontend)
- Docker & Docker Compose (선택 사항/optional)

## Setup
1. `python -m venv .venv && source .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `.env` 파일에 AI API 키와 데이터베이스/캐시 DSN 설정
4. (선택 사항) `npm install` inside `web_frontend/`

## Quick Start
```bash
# 가장 빠르게 전체 시스템 실행하는 방법
python main.py --package lodash
```

## Pipeline at a Glance
1. MappingCollector → CVE 수집(Collect CVEs)
2. EPSSFetcher → 위험 점수 조회(Get EPSS scores)
3. ThreatAgent → 공격 사례 탐색(Search threat cases)
4. ThreatAgent → Claude 요약(Summarize findings)
5. Analyzer → 위험 등급/권고 산출(Calculate risk & advice)
6. QueryAPI/WebFrontend → 결과 제공(Present results)

## Documentation
- 더 자세한 내용은 `docs/ARCHITECTURE.md`, `docs/API.md` 참고

## License
- MIT License
