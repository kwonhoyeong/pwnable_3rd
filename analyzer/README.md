# Analyzer 모듈 가이드 (Analyzer Module Guide)

## 개요(Overview)
- 역할(Role): CVE, EPSS 점수, 공격 사례 데이터를 입력받아 위험 등급과 대응 권고를 생성합니다.
- 실행 형태(Runtime): FastAPI 서비스 + 규칙 기반 분석 로직 + AI 보조 권고 텍스트 생성.

## 사전 준비(Prerequisites)
1. PostgreSQL 연결 문자열 (예: `postgresql+asyncpg://user:pass@localhost:5432/analyzer`).
2. (선택) Claude 또는 GPT-5 API 키.
3. `.env` 예시:
   ```env
   DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/analyzer
   CLAUDE_API_KEY=...
   GPT5_API_KEY=...
   ```

## 설치 및 실행(Setup & Run)
```bash
pip install -r requirements.txt
python -m uvicorn analyzer.app.main:app --reload
```
- 헬스 체크: `curl http://127.0.0.1:8003/health`

## 분석 요청 테스트(Analysis request test)
```bash
curl -X POST http://127.0.0.1:8003/analyze \
  -H "Content-Type: application/json" \
  -d '{
        "cve_id": "CVE-2023-1234",
        "epss_score": 0.87,
        "cases": [],
        "package": "lodash",
        "version_range": "<4.17.21"
      }'
```
- 응답 예시(Expected response):
  ```json
  {
    "cve_id": "CVE-2023-1234",
    "risk_level": "High",
    "recommendations": [
      "Apply the latest patch",
      "Increase monitoring"
    ],
    "analysis_summary": "…",
    "generated_at": "2025-10-24T12:42:00Z"
  }
  ```

## 규칙 엔진(Rule engine)
- `AnalyzerService.calculate_risk_level` 에서 EPSS 임계값 및 사례 수를 기준으로 위험도를 판정합니다.
- `AnalyzerService.generate_recommendations` 는 AI 클라이언트와 규칙 기반 텍스트를 혼합합니다.

## 데이터베이스(Database)
- 스키마 파일: `db/schema.sql`.
- 테이블: `analysis_results(cve_id PRIMARY KEY, package TEXT, risk_level TEXT, recommendations JSONB, analysis_summary TEXT, generated_at TIMESTAMP)`.

## Docker 실행(Docker Run)
```bash
docker build -t analyzer .
docker run --rm -p 8003:8000 --env-file ../.env analyzer
```

