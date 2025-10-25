# QueryAPI 모듈 가이드 (QueryAPI Module Guide)

## 개요(Overview)
- 역할(Role): 패키지명 또는 CVE ID를 기준으로 여러 데이터 소스(매핑, EPSS, 분석 결과)를 통합 조회합니다.
- 실행 형태(Runtime): FastAPI 기반 REST API + Redis 캐싱.

## 사전 준비(Prerequisites)
1. PostgreSQL 연결 문자열.
2. Redis 연결 URL (예: `redis://localhost:6379/1`).
3. `.env` 예시:
   ```env
   DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/query
   REDIS_URL=redis://localhost:6379/1
   ```

## 설치 및 실행(Setup & Run)
```bash
pip install -r requirements.txt
python -m uvicorn query_api.app.main:app --reload
```
- 헬스 체크: `curl http://127.0.0.1:8004/health`

## 조회 테스트(Query tests)
1. 패키지 기준 검색(By package):
   ```bash
   curl "http://127.0.0.1:8004/api/v1/query?package=lodash"
   ```
2. CVE 기준 검색(By CVE):
   ```bash
   curl "http://127.0.0.1:8004/api/v1/query?cve_id=CVE-2023-1234"
   ```
- 응답 예시(Expected JSON):
  ```json
  {
    "package": "lodash",
    "cve_list": [
      {
        "cve_id": "CVE-2023-1234",
        "epss_score": 0.87,
        "risk_level": "High",
        "analysis_summary": "…",
        "recommendations": [
          "Apply the latest patch"
        ]
      }
    ]
  }
  ```

## 캐시 전략(Cache strategy)
- `QueryService` 가 Redis에 패키지/ID별 결과를 JSON 문자열로 저장하여 재사용합니다.
- 만료 정책(TTL)은 `.env`의 `CACHE_TTL_SECONDS` 로 조정 가능합니다.

## 데이터베이스(Database)
- 내부적으로 다른 모듈의 테이블 뷰/머티리얼라이즈드를 참조하는 것을 가정하며, 샘플 스키마는 `db/schema.sql` 에 정리되어 있습니다.

## Docker 실행(Docker Run)
```bash
docker build -t query-api .
docker run --rm -p 8004:8000 --env-file ../.env query-api
```

