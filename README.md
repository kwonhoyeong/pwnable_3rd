# NPM Supply Chain Security Pipeline

NPM 패키지의 CVE 취약점을 수집하고, CVSS/EPSS 점수를 분석하여 패치 우선순위를 자동으로 산정하는 보안 파이프라인입니다.

## Quick Start (3분 안에 시작하기)

### 1. 저장소 클론 및 환경 설정
```bash
git clone <your-repo-url>
cd pwnable_3rd
cp .env.example .env
```

### 2. Docker로 한 번에 실행
```bash
docker-compose up -d
```

### 3. 테스트 확인
```bash
# API 테스트
curl http://localhost:8004/api/v1/query?package=lodash

# 웹 대시보드
# 브라우저에서 http://localhost:5173 접속
```

## 프로젝트 구조

```
├── main.py                 # 파이프라인 오케스트레이터
├── common_lib/             # 공통 라이브러리 (AI 클라이언트, DB, 로깅)
├── mapping_collector/      # NPM CVE 매핑 수집기
├── cvss_fetcher/          # CVSS 점수 조회
├── epss_fetcher/          # EPSS 위험도 조회
├── threat_agent/          # LLM 기반 위협 분석
├── analyzer/              # 종합 위험도 분석 및 우선순위 산정
├── query_api/             # REST API 서버
├── web_frontend/          # React 대시보드
└── docs/                  # 상세 문서
```

## Requirements

- **Docker & Docker Compose** (권장)
- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Node.js 18+ (웹 프론트엔드)

## 환경 변수 설정

`.env` 파일에 다음 항목을 설정하세요:

```env
# AI API Keys (선택 사항 - ThreatAgent 사용 시 필요)
NT_PERPLEXITY_API_KEY=your_key_here
NT_CLAUDE_API_KEY=your_key_here
NT_GPT5_API_KEY=your_key_here

# Database (Docker 사용 시 자동 설정됨)
NT_POSTGRES_DSN=postgresql+asyncpg://ntuser:ntpass@postgres:5432/threatdb
NT_REDIS_URL=redis://redis:6379/0
```

## 파이프라인 실행 방법

### Option 1: Docker Compose (가장 간단)
```bash
docker-compose up -d
```

### Option 2: 로컬에서 직접 실행
```bash
# 1. 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. PostgreSQL & Redis 실행 (별도)
# 4. DB 초기화
psql -U ntuser -d threatdb -f init-db.sql

# 5. 파이프라인 실행
python main.py --package lodash
```

### Option 3: Helper Script 사용
```bash
# 의존성 자동 설치 + 실행
bash run_pipeline.sh --package lodash --install-deps

# ThreatAgent 생략하고 실행
bash run_pipeline.sh --package lodash --skip-threat-agent
```

## 파이프라인 단계

1. **MappingCollector** - NPM 패키지의 CVE 수집
2. **CVSSFetcher** - CVSS 기본 점수 조회
3. **EPSSFetcher** - EPSS 공격 가능성 점수 조회
4. **ThreatAgent** - LLM 기반 실제 공격 사례 분석
5. **Analyzer** - 종합 위험도 산정 및 패치 우선순위 계산
6. **QueryAPI/WebFrontend** - 결과 조회 및 시각화

## 서비스 포트

| 서비스 | 포트 | 설명 |
|--------|------|------|
| MappingCollector | 8000 | CVE 매핑 수집 |
| CVSSFetcher | 8006 | CVSS 점수 조회 |
| EPSSFetcher | 8001 | EPSS 점수 조회 |
| ThreatAgent | 8002 | 위협 분석 |
| Analyzer | 8003 | 종합 분석 |
| QueryAPI | 8004 | REST API |
| WebFrontend | 5173 | 대시보드 |
| PostgreSQL | 5432 | 데이터베이스 |
| Redis | 6379 | 캐시 |

## 문서

- [아키텍처 상세 설명](docs/ARCHITECTURE.md)
- [API 명세](docs/API.md)
- [Docker 가이드](docs/DOCKER.md)
- [팀원 개발 환경 가이드](SETUP.md)

## 개발 가이드

### 로그 확인
```bash
# 전체 로그
docker-compose logs -f

# 특정 서비스
docker-compose logs -f analyzer
```

### 서비스 재시작
```bash
docker-compose restart analyzer
```

### DB 접속
```bash
docker-compose exec postgres psql -U ntuser -d threatdb
```

### 헬스체크
```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8004/health
```

## ⚠️ 주의사항

1. `.env` 파일은 절대 커밋하지 마세요 (API 키 포함)
2. 포트 충돌 시 `docker-compose down` 후 재시작
3. 데이터 초기화: `docker-compose down -v` (주의: 모든 데이터 삭제)

## 📄 License

MIT License
