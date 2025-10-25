# ThreatAgent 모듈 가이드 (ThreatAgent Module Guide)

## 개요(Overview)
- 역할(Role): Perplexity API로 최신 공격 정보를 탐색하고 Claude/GPT-5로 요약하여 사례 데이터베이스에 축적합니다.
- 실행 형태(Runtime): FastAPI 서비스 + 내부 서비스 계층.
- 핵심 구성 요소(Keys): `SearchService`, `SummaryService`, `CaseRepository`, `prompts.py` 템플릿.

## 사전 준비(Prerequisites)
1. AI API 키 환경 변수:
   ```env
   PERPLEXITY_API_KEY=...
   CLAUDE_API_KEY=...
   GPT5_API_KEY=...
   ```
2. PostgreSQL 연결 문자열.
3. (선택) Redis 캐시 URL.

## 설치 및 실행(Setup & Run)
```bash
pip install -r requirements.txt
python -m uvicorn threat_agent.app.main:app --reload
```
- 헬스 체크: `curl http://127.0.0.1:8002/health`

## 기능 테스트(Function testing)
1. 검색+요약 체인 테스트(Chain test):
   ```bash
   curl -X POST http://127.0.0.1:8002/collect \
     -H "Content-Type: application/json" \
     -d '{
       "cve_id": "CVE-2023-1234",
       "package": "lodash",
       "version_range": "<4.17.21"
     }'
   ```
2. 예상 응답(Expected response skeleton):
   ```json
   {
     "cve_id": "CVE-2023-1234",
     "package": "lodash",
     "version_range": "<4.17.21",
     "cases": [
       {
         "source": "https://example.com/exploit-detail",
         "title": "Exploitation of CVE-2023-1234 in lodash",
         "date": "2025-10-10",
         "summary": "Attackers chained …",
         "collected_at": "2025-10-24T12:40:00Z"
       }
     ]
   }
   ```

## 중복 방지(Deduplication)
- `CaseRepository.save_cases` 에서 기존 URL/제목을 비교하여 중복을 제거합니다.

## 데이터베이스(Database)
- 스키마: `db/schema.sql`.
- 테이블: `threat_cases(id SERIAL, cve_id TEXT, package TEXT, version_range TEXT, source TEXT, title TEXT, summary TEXT, collected_at TIMESTAMP)`.

## Docker 실행(Docker Run)
```bash
docker build -t threat-agent .
docker run --rm -p 8002:8000 --env-file ../.env threat-agent
```

## 프롬프트 템플릿(Prompt templates)
- 탐색(Search): `SEARCH_PROMPT_TEMPLATE` → Perplexity API에 전달.
- 요약(Summarize): `SUMMARY_PROMPT_TEMPLATE` → Claude/GPT-5 API로 전달.

