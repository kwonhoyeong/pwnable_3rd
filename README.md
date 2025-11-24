# npm 공급망 CVE/EPSS 대응 파이프라인

NPM 생태계에서 발견되는 취약성(CVE)에 대해 CVSS/EPSS 점수를 수집하고, 멀티 에이전트 기반 AI 분석을 통해 위험도를 계산한 뒤 API·대시보드로 노출하는 프로토타입입니다.

## 저장소 구조
```
  ├── main.py                  # CLI 진입점
  ├── common_lib/              # 공통 모델/유틸
  ├── mapping_collector/       # CVE 맵핑 에이전트
  ├── cvss_fetcher/            # CVSS 수집기
  ├── epss_fetcher/            # EPSS 수집기
  ├── threat_agent/            # 위협 인텔리전스 수집
  ├── analyzer/                # AI 분석 및 리포트 생성
  ├── query_api/               # FastAPI 기반 API 서버
  ├── web_frontend/            # Vite/React 대시보드
  ├── demo/                    # 샘플 데이터 및 스크립트
  └── .env.example             # 환경 변수 템플릿
```

## 필수 요구 사항
- Python 3.11 이상
- PostgreSQL 14 이상
- Redis 6 이상
- Node.js 18 이상 (Vite 프론트엔드)
- FastAPI 0.121.x, Uvicorn 0.38.x, React 18.3.x (세부 버전은 `requirements.txt`, `web_frontend/package.json` 참고)

## 환경 변수 준비 (.env)
프로젝트 루트에서 `.env.example`을 복사한 뒤 다음 항목을 채워야 합니다.

```dotenv
# Database & Cache
NT_POSTGRES_DSN=postgresql+asyncpg://<user>:<password>@localhost:5432/threatdb
NT_REDIS_URL=redis://localhost:6379/0

# AI API Keys (GPT 기반 분석에 하나 이상 필수)
NT_GPT5_API_KEY=sk-REPLACE_WITH_YOUR_OPENAI_API_KEY
NT_PERPLEXITY_API_KEY=your-perplexity-key-here
NT_CLAUDE_API_KEY=your-claude-key-here

# QueryAPI 인증 키 (콤마 구분)
NT_QUERY_API_KEYS=dev-api-key-123,admin-key-456
NT_ENVIRONMENT=development

# Feature Toggles (인프라 준비 후 true)
NT_ALLOW_EXTERNAL_CALLS=false
NT_ENABLE_DATABASE=false
NT_ENABLE_CACHE=false
```

### API 키 주의 사항
- `NT_GPT5_API_KEY`가 없으면 AI 분석 단계가 대체 메시지(`AI 분석 실패로 수동 검토 필요`)로 대체됩니다.
- 인증 오류(401/400)가 로그에 보이면 키 값 및 권한을 다시 확인하세요.

## 로컬 개발 환경 설정
1. `python3 -m venv .venv && source .venv/bin/activate`
2. `python3 -m pip install -r requirements.txt`
3. `cp .env.example .env` 후 데이터베이스·캐시 DSN 및 API 키를 입력합니다.
4. (선택) `web_frontend/`에서 `npm install`로 UI 의존성을 설치합니다.

## Docker Compose로 전체 시스템 실행
웹 프론트엔드, Query API, 워커를 한 번에 올리는 권장 방법입니다.

1. `.env` 파일을 준비하고 필요한 API 키(특히 `NT_GPT5_API_KEY`, `NVD_API_KEY`, `NT_QUERY_API_KEYS`)를 기입합니다.
2. `docker-compose up -d --build`
3. 접속 경로
   - Web Frontend: [http://localhost:5173](http://localhost:5173)
   - Query API Docs: [http://localhost:8004/docs](http://localhost:8004/docs)
   - RabbitMQ UI: [http://localhost:15672](http://localhost:15672) (guest/guest)
4. 분석 트리거 예시
   ```bash
   docker exec npm-threat-redis redis-cli RPUSH analysis_tasks '{"package": "lodash", "version": "4.17.19", "force": true}'
   ```
5. 종료 시 `docker-compose down`

## main.py 직접 실행
1. PostgreSQL에서 `threatdb`를 만들고 각 모듈의 `db/schema.sql`을 순서대로 실행합니다.
2. Redis(기본 포트 6379)와 `.env` 설정을 준비합니다.
3. 가상환경을 활성화한 뒤 `python3 main.py --package lodash`로 파이프라인을 실행합니다.

## Quick Start & CLI 옵션
```bash
# 전체 파이프라인 실행
python3 main.py --package lodash

# 캐시 무시 후 새 분석
python3 main.py --package lodash --force

# ThreatAgent 단계를 생략
python3 main.py --package lodash --skip-threat-agent
```

- `--package` (필수): 분석 대상 npm 패키지명
- `--version-range` (선택): 기본값 `latest`
- `--force`: 모든 캐시를 무시하고 API 호출을 강제
- `--skip-threat-agent`: 위협 사례 수집 스킵 후 안전한 기본값 사용

## Helper 스크립트 `run_pipeline.sh`
```bash
# 최초 실행 시 의존성 설치 포함
bash run_pipeline.sh --package lodash --install-deps

# ThreatAgent 생략
bash run_pipeline.sh --package lodash --skip-threat-agent

# 실행 권한 부여 예시
chmod +x run_pipeline.sh
./run_pipeline.sh --package lodash
```
> `.env`가 준비되어 있어야 하며 필요 시 `--python` 옵션으로 다른 인터프리터를 지정할 수 있습니다.

## 파이프라인 흐름 요약
1. `AgentOrchestrator`: 에이전트 실행 순서를 정의하고 상태를 브로드캐스트
2. `MappingAgent`: 패키지/버전으로 CVE를 조회하고 캐시합니다.
3. `CVSSAgent` & `EPSSAgent`: `asyncio.gather`로 병렬 수행하며 점수를 조회 후 저장합니다.
4. `ThreatAgent`: Perplexity/커스텀 API에서 위협 사례를 수집하거나 기본값으로 대체합니다.
5. `Analyzer`: Claude + GPT5로 Markdown 리포트를 생성하고 `CVSS*0.4 + (EPSS*10)*0.3 + AI Score*0.3` 가중치 기반 `risk_score`를 산출합니다.
6. `QueryAPI`/`WebFrontend`: Redis·PostgreSQL을 조회해 `/api/v1/query`, `/api/v1/history`, `/api/v1/stats`를 제공하고 대시보드에서 시각화합니다.

### QueryAPI 엔드포인트 (v1)
- `GET /api/v1/query?package=<name>|cve_id=<id>`: 단건 조회 + 우선순위 스코어
- `GET /api/v1/history?skip=0&limit=10`: AI 분석 이력과 `risk_score` 목록
- `GET /api/v1/stats`: 위험도 분포(critical/high/medium/low/unknown) 및 전체 스캔 수
- 모든 응답은 `X-Request-ID` 헤더와 `{"error": {...}}` 형태의 표준 에러를 따릅니다.

### Web Frontend (Vite/React 18.3)
- Tailwind 토큰(`web_frontend/src/styles/`)과 `components/ui`에 버튼·배지·카드 컴포넌트를 정의
- `DashboardPage`는 `SearchBar`, `StatsCards`, `RiskDistributionChart`, `RecentScansTable`을 조합해 API 응답을 시각화
- `web_frontend/src/api/client.ts`는 `VITE_API_URL`, `VITE_QUERY_API_URL` 환경 변수와 자동 `X-Request-ID` 주입을 지원

## 시스템 상태

### 동작 중인 기능
- 다중 에이전트 파이프라인 오케스트레이션
- CVE/CVSS/EPSS 수집 및 폴백 처리
- 위협 인텔리전스 집계 (API 키 구성 시)
- AI 기반 Markdown 분석과 가중치 위험 점수 계산
- PostgreSQL 저장 및 인메모리 폴백
- Redis 캐시와 장애 허용
- `X-API-Key` 인증 + slowapi 기반 Rate Limiting
- `/query`·`/history`·`/stats` 엔드포인트 및 Request ID 미들웨어
- React 대시보드 + REST API 클라이언트 (자동 Request ID)
- 오류/로그 처리 개선 및 단계별 폴백

### 알려진 제한 사항
- Redis가 없을 경우 성능이 낮아지나 파이프라인은 계속 동작합니다.
- PostgreSQL이 연결되지 않으면 경고를 남기고 인메모리 저장소로 전환합니다.
- API 키가 누락되면 아래와 같이 폴백 데이터가 사용됩니다.
  - `NT_PERPLEXITY_API_KEY`: 위협 사례 기본값
  - `NT_GPT5_API_KEY`: AI 권고 기본값
  - 외부 API 차단: EPSS/CVSS 기본값(0.0)
- 기본적으로 외부 API/Redis/PostgreSQL 호출은 비활성화되어 있으며 필요 시
  - `NT_ALLOW_EXTERNAL_CALLS=true`
  - `NT_ENABLE_DATABASE=true`
  - `NT_ENABLE_CACHE=true`
  로 활성화합니다.

### 최근 갱신 사항 (2025-02-15)
- MappingScheduler가 `AsyncSession`을 안전하게 사용해 `async_generator` 오류 제거
- 대시보드를 위한 위험도 우선순위가 대문자 `CRITICAL/HIGH` 값도 정확히 처리
- 프론트엔드 API 클라이언트가 `VITE_API_URL`/`VITE_QUERY_API_URL`을 존중하고 `X-Request-ID`를 백필
- FastAPI 0.121.x, Uvicorn 0.38.x, React 18.3.x, axios 1.13.x 등 의존성 최신화
- 문서 갱신: 가중치 계산식, 신규 엔드포인트, 프론트엔드 스택 설명

## 추가 문서
- `docs/ARCHITECTURE.md`: 전체 시스템 아키텍처
- `docs/API.md`: REST API 상세 명세
- `docs/REVIEW.md`: 분석 체크리스트 및 품질 기준

## License
- MIT License
