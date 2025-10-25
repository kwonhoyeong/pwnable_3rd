# EPSSFetcher 모듈 가이드 (EPSSFetcher Module Guide)

## 개요(Overview)
- 역할(Role): CVE ID를 입력받아 EPSS 공식 API로부터 최신 점수를 가져와 정규화하여 저장합니다.
- 실행 형태(Runtime): FastAPI 마이크로서비스.
- 주요 의존성(Core deps): Python 3.11, FastAPI, httpx, PostgreSQL.

## 사전 준비(Prerequisites)
1. PostgreSQL 연결 문자열 (예: `postgresql+asyncpg://user:pass@localhost:5432/epss`).
2. `.env` 환경 변수:
   ```env
   DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/epss
   EPSS_BASE_URL=https://api.first.org/data/v1/epss
   ```

## 설치 및 실행(Setup & Run)
```bash
pip install -r requirements.txt
python -m uvicorn epss_fetcher.app.main:app --reload
```
- 헬스 체크: `curl http://127.0.0.1:8001/health`

## API 테스트(API Testing)
- 단일 CVE 점수 요청(Post request):
  ```bash
  curl -X POST http://127.0.0.1:8001/fetch \
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
- 외부 오케스트레이터에서 주기적으로 `/fetch` 엔드포인트 호출 가능.

