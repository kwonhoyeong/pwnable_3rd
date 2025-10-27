# EPSSFetcher 모듈 가이드 (EPSSFetcher Module Guide)

## 개요(Overview)
- 역할(Role): CVE ID를 입력받아 EPSS 공식 API로부터 최신 점수를 가져와 정규화하여 저장합니다.
- 실행 형태(Runtime): FastAPI 마이크로서비스.
- 주요 의존성(Core deps): Python 3.11, FastAPI, httpx, PostgreSQL.

## 사전 준비(Prerequisites)
1. PostgreSQL 인스턴스 및 Redis가 실행 중이어야 합니다(PostgreSQL & Redis running).
2. 루트 `.env` 파일에 다음 값을 지정합니다(Set values in root `.env`):
   ```env
   NT_POSTGRES_DSN=postgresql+asyncpg://user:pass@localhost:5432/threatdb
   NT_REDIS_URL=redis://localhost:6379/0
   ```
   > EPSS API 기본 URL은 코드에서 기본값(`https://epss.cyentia.com/api/epss`)을 사용합니다. 필요 시 `EPSSService` 생성자에 전달하세요.

## 설치 및 실행(Setup & Run)
```bash
cd ..
python3 -m pip install -r requirements.txt
python3 -m uvicorn epss_fetcher.app.main:app --reload
```
- 헬스 체크: `curl http://127.0.0.1:8001/health`

## API 테스트(API Testing)
- 단일 CVE 점수 요청(Post request):
  ```bash
  curl -X POST http://127.0.0.1:8001/api/v1/epss \
    -H "Content-Type: application/json" \
    -d '{"cve_id": "CVE-2023-1234"}'
  ```
- 예상 응답(Expected response):
  ```json
  {
    "cve_id": "CVE-2023-1234",
    "epss_score": 0.87,
    "collected_at": "2025-10-24T12:34:56Z"
  }
  ```

## 재시도/예외 처리(Retry & Error handling)
- `EPSSService.fetch_score` 내에 지수 백오프(exponential backoff) 기반 재시도 로직이 포함될 예정입니다.
- 실패 시 FastAPI 예외가 적절히 포맷되어 반환됩니다.

## 데이터베이스(Database)
- 스키마 파일: `db/schema.sql`.
- 핵심 테이블: `epss_scores(cve_id PRIMARY KEY, epss_score NUMERIC, collected_at TIMESTAMP)`.

## Docker 실행(Docker Run)
```bash
docker build -t epss-fetcher .
docker run --rm -p 8001:8000 --env-file ../.env epss-fetcher
```

## 샘플 스케줄 사용(Sample scheduling)
- 외부 오케스트레이터에서 주기적으로 `/api/v1/epss` 엔드포인트를 호출할 수 있습니다.

