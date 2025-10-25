# API SPECIFICATION

## MappingCollector
- Endpoint: `POST /collect`
- Request JSON:
  ```json
  {
    "package": "lodash",
    "version_range": "<4.17.21",
    "collected_at": "2025-10-24T12:34:56Z"
  }
  ```
- Response JSON:
  ```json
  {
    "package": "lodash",
    "version_range": "<4.17.21",
    "cve_ids": ["CVE-2023-1234"],
    "collected_at": "2025-10-24T12:34:56Z"
  }
  ```
- Errors:
  - `400` 유효성 오류(Validation error)
  - `500` 내부 서버 오류(Internal server error)

## EPSSFetcher
- Endpoint: `POST /epss`
- Request JSON:
  ```json
  {"cve_id": "CVE-2023-1234"}
  ```
- Response JSON:
  ```json
  {
    "cve_id": "CVE-2023-1234",
    "epss_score": 0.87,
    "collected_at": "2025-10-24T12:34:56Z"
  }
  ```
- Errors:
  - `400` 잘못된 입력(Bad request)
  - `502` 외부 API 실패(Upstream failure)

## ThreatAgent
- Endpoint: `POST /threats`
- Request JSON:
  ```json
  {
    "cve_id": "CVE-2023-1234",
    "package": "lodash",
    "version_range": "<4.17.21"
  }
  ```
- Response JSON:
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
- Errors:
  - `400` 입력 오류(Input error)
  - `504` AI 응답 지연(AI timeout)

## Analyzer
- Endpoint: `POST /analyze`
- Request JSON:
  ```json
  {
    "cve_id": "CVE-2023-1234",
    "epss_score": 0.87,
    "cases": [],
    "package": "lodash",
    "version_range": "<4.17.21"
  }
  ```
- Response JSON:
  ```json
  {
    "cve_id": "CVE-2023-1234",
    "risk_level": "High",
    "recommendations": ["..."],
    "analysis_summary": "...",
    "generated_at": "2025-10-24T12:42:00Z"
  }
  ```
- Errors:
  - `400` 입력 오류(Input error)
  - `500` 분석 실패(Analysis failure)

## QueryAPI
- Endpoint: `GET /api/v1/query`
- Query Parameters: `package` 또는 `cve_id` 필수
- Response JSON:
  ```json
  {
    "package": "lodash",
    "cve_list": [
      {
        "cve_id": "CVE-2023-1234",
        "epss_score": 0.87,
        "risk_level": "High",
        "analysis_summary": "…",
        "recommendations": ["…"]
      }
    ]
  }
  ```
- Errors:
  - `400` 파라미터 누락(Missing parameters)
  - `404` 데이터 없음(Not found)
  - `500` 서버 오류(Server error)

## Authentication
- 현재 버전은 API 키 인증 없음(No authentication yet). 향후 서비스 토큰 추가 예정.

## Error Envelope
- 실패 시 응답 형식:
  ```json
  {
    "error_code": "SERVICE_UNAVAILABLE",
    "message": "상세 오류 메시지",
    "timestamp": "2025-10-24T12:34:56Z"
  }
  ```
