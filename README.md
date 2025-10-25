# npm 공급망 CVE/EPSS 대응 파이프라인

## Repository Layout
```
  ├── main.py
  ├── docker-compose.yml
  ├── init-db.sql
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
3. `cp .env.example .env` 후 AI API 키와 데이터베이스/캐시 DSN을 설정
4. (선택 사항) `npm install` inside `web_frontend/`

## Quick Start
```bash
# 가장 빠르게 전체 시스템 실행하는 방법
python main.py --package lodash
```

## Docker 개발 환경

#### 📦 개발 환경 세팅 (초기 1회)
```bash
# 1. 저장소 클론
git clone <repository-url>
cd npm-threat-evaluator

# 2. 환경변수 설정
cp .env.example .env
# .env 파일을 열어서 본인의 API 키를 입력하세요

# 3. Docker 컨테이너 빌드 및 실행
docker-compose up -d

# 4. 서비스 헬스체크
curl http://localhost:8000/health  # MappingCollector
curl http://localhost:8001/health  # EPSSFetcher
curl http://localhost:8002/health  # ThreatAgent
curl http://localhost:8003/health  # Analyzer
curl http://localhost:8004/health  # QueryAPI

# 5. 프론트엔드 접속
http://localhost:5173
```

#### 🔧 일상적인 개발 워크플로우
```bash
# 개발 시작
docker-compose up -d

# 특정 서비스만 재시작
docker-compose restart analyzer

# 로그 실시간 확인
docker-compose logs -f threat-agent

# DB 접속
docker-compose exec postgres psql -U ntuser -d threatdb

# Redis CLI
docker-compose exec redis redis-cli

# 전체 종료
docker-compose down

# 볼륨까지 완전 삭제 (주의!)
docker-compose down -v
```

#### ⚡ 핫 리로드 (Hot Reload)
모든 Python 서비스는 `--reload` 옵션으로 실행되므로:
- Python 파일 수정 → 저장 → **자동 재시작** ✅
- React 파일 수정 → 저장 → **즉시 반영** ✅

#### 🐛 트러블슈팅
```bash
# 포트 충돌 시
docker-compose down
lsof -ti:8000 | xargs kill -9

# DB 초기화 실패 시
docker-compose down -v
docker-compose up -d postgres
docker-compose logs postgres

# 빌드 캐시 문제
docker-compose build --no-cache
docker-compose up -d
```

## Pipeline at a Glance
1. MappingCollector → CVE 수집(Collect CVEs)
2. EPSSFetcher → 위험 점수 조회(Get EPSS scores)
3. ThreatAgent → 공격 사례 탐색(Search threat cases)
4. ThreatAgent → Claude 요약(Summarize findings)
5. Analyzer → 위험 등급/권고 산출(Calculate risk & advice)
6. QueryAPI/WebFrontend → 결과 제공(Present results)

## Documentation
- 더 자세한 내용은 `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/DOCKER.md` 참고

## License
- MIT License
