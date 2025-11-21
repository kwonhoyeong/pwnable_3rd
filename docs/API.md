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
- Endpoint: `POST /api/v1/epss`
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

## CVSSFetcher
- Endpoint: `POST /api/v1/cvss`
- Request JSON:
  ```json
  {"cve_id": "CVE-2023-1234"}
  ```
- Response JSON:
  ```json
  {
    "cve_id": "CVE-2023-1234",
    "cvss_score": 9.8,
    "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
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
    "cvss_score": 9.8,
    "cases": [],
    "package": "lodash",
    "version_range": "<4.17.21"
  }
  ```
- Response JSON:
  ```json
  {
    "cve_id": "CVE-2023-1234",
    "risk_level": "CRITICAL",
    "risk_score": 8.7,
    "recommendations": ["..."],
    "analysis_summary": "...",
    "generated_at": "2025-10-24T12:42:00Z"
  }
  ```
- Errors:
  - `400` 입력 오류(Input error)
  - `500` 분석 실패(Analysis failure)

## QueryAPI
- `GET /api/v1/query`: Package or CVE lookups (query params: `package` or `cve_id`)
  - Response:
    ```json
    {
      "package": "lodash",
      "cve_list": [
        {
          "cve_id": "CVE-2023-1234",
          "epss_score": 0.87,
          "cvss_score": 9.8,
          "risk_level": "CRITICAL",
          "analysis_summary": "…",
          "recommendations": ["…"],
          "priority_score": 345.0,
          "priority_label": "P1"
        }
      ]
    }
    ```
- `GET /api/v1/history`: Paginated analysis history
  - Query params: `skip` (default 0), `limit` (default 10, max 100)
  - Response:
    ```json
    {
      "skip": 0,
      "limit": 10,
      "total_returned": 2,
      "records": [
        {
          "cve_id": "CVE-2023-1234",
          "risk_level": "CRITICAL",
          "risk_score": 8.7,
          "analysis_summary": "…",
          "recommendations": ["…"],
          "generated_at": "2025-10-24T12:42:00Z",
          "created_at": "2025-10-24T12:42:00Z"
        }
      ]
    }
    ```
- `GET /api/v1/stats`: Aggregated risk distribution
  - Response:
    ```json
    {
      "total_scans": 250,
      "risk_distribution": {
        "CRITICAL": 15,
        "HIGH": 45,
        "MEDIUM": 120,
        "LOW": 60,
        "Unknown": 10
      }
    }
    ```
- Errors:
  - `400` 파라미터 누락(Missing parameters)
  - `404` 데이터 없음(Not found)
  - `503` 외부 서비스 오류(Database/cache unavailable)
  - `500` 서버 오류(Server error)

## Authentication
- 현재 버전은 API 키 인증 없음(No authentication yet). 향후 서비스 토큰 추가 예정.

## Error Envelope
- 실패 시 표준 응답 형식:
  ```json
  {
    "error": {
      "code": "SERVICE_UNAVAILABLE",
      "message": "상세 오류 메시지",
      "details": {},
      "request_id": "f3f8c83e-..."
    }
  }
  ```
