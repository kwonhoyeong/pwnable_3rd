# API 명세서

## MappingCollector
- 엔드포인트: `POST /collect`
- 요청 JSON:
  ```json
  {
    "package": "lodash",
    "version_range": "<4.17.21",
    "collected_at": "2025-10-24T12:34:56Z"
  }
  ```
- 응답 JSON:
  ```json
  {
    "package": "lodash",
    "version_range": "<4.17.21",
    "cve_ids": ["CVE-2023-1234"],
    "collected_at": "2025-10-24T12:34:56Z"
  }
  ```
- 오류:
  - `400` 유효성 오류
  - `500` 내부 서버 오류

## EPSSFetcher
- 엔드포인트: `POST /api/v1/epss`
- 요청 JSON:
  ```json
  {"cve_id": "CVE-2023-1234"}
  ```
- 응답 JSON:
  ```json
  {
    "cve_id": "CVE-2023-1234",
    "epss_score": 0.87,
    "collected_at": "2025-10-24T12:34:56Z"
  }
  ```
- 오류:
  - `400` 잘못된 입력
  - `502` 외부 API 실패

## CVSSFetcher
- 엔드포인트: `POST /api/v1/cvss`
- 요청 JSON:
  ```json
  {"cve_id": "CVE-2023-1234"}
  ```
- 응답 JSON:
  ```json
  {
    "cve_id": "CVE-2023-1234",
    "cvss_score": 9.8,
    "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    "collected_at": "2025-10-24T12:34:56Z"
  }
  ```
- 오류:
  - `400` 잘못된 입력
  - `502` 외부 API 실패

## ThreatAgent
- 엔드포인트: `POST /threats`
- 요청 JSON:
  ```json
  {
    "cve_id": "CVE-2023-1234",
    "package": "lodash",
    "version_range": "<4.17.21"
  }
  ```
- 응답 JSON:
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
- 오류:
  - `400` 입력 오류
  - `504` AI 응답 지연

## Analyzer
- 엔드포인트: `POST /analyze`
- 요청 JSON:
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
- 응답 JSON:
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
- 오류:
  - `400` 입력 오류
  - `500` 분석 실패

## QueryAPI

### 인증
**모든 QueryAPI 엔드포인트는 `X-API-Key` 헤더를 통한 인증이 필요합니다.**

예시:
```bash
curl -H "X-API-Key: dev-api-key-123" http://localhost:8004/api/v1/query?package=lodash
```

- 유효한 API 키는 `NT_QUERY_API_KEYS` 환경 변수를 통해 설정됩니다 (쉼표로 구분된 목록).
- 키가 누락되거나 유효하지 않으면 `401 Unauthorized` 또는 `403 Forbidden`을 반환합니다.

### Rate Limiting (속도 제한)
- `/api/v1/query`: 분당 5회
- `/api/v1/history`: 분당 10회
- `/api/v1/stats`: 분당 5회

제한 초과 시 `429 Too Many Requests`를 반환합니다.

### 엔드포인트

#### `GET /api/v1/query`
패키지 또는 CVE 조회

**쿼리 파라미터:**
- `package` (선택): 패키지 이름 (예: "lodash")
- `cve_id` (선택): CVE 식별자 (예: "CVE-2023-1234")
- `version` (선택): 패키지 버전 (예: "1.0.0"). 지정하지 않으면 기본값 "latest"
- `ecosystem` (선택, 기본값: "npm"): 패키지 생태계. 지원: "npm", "pip", "apt"
- `force` (선택, 기본값: false): 기존 분석 결과를 무시하고 강제 재분석

**응답:**
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
      "risk_score": 85.7,
      "risk_label": "P1"
    }
  ]
}
```

**참고:** 응답 스키마가 `priority_score`/`priority_label`에서 `risk_score`/`risk_label`로 변경되었습니다.

#### `GET /api/v1/history`
페이지네이션된 분석 히스토리

**쿼리 파라미터:**
- `skip` (기본값: 0): 건너뛸 레코드 수
- `limit` (기본값: 10, 최대: 100): 반환할 레코드 수

**응답:**
```json
{
  "skip": 0,
  "limit": 10,
  "total_returned": 2,
  "records": [
    {
      "cve_id": "CVE-2023-1234",
      "risk_level": "CRITICAL",
      "risk_score": 85.7,
      "analysis_summary": "…",
      "recommendations": ["…"],
      "generated_at": "2025-10-24T12:42:00Z",
      "created_at": "2025-10-24T12:42:00Z"
    }
  ]
}
```

#### `GET /api/v1/stats`
집계된 위험도 분포

**응답:**
```json
{
  "total_scans": 250,
  "risk_distribution": {
    "CRITICAL": 15,
    "HIGH": 45,
    "MEDIUM": 120,
    "LOW": 60,
    "UNKNOWN": 10
  }
}
```

**참고:** 
- `risk_distribution`의 모든 키는 대문자(UPPERCASE)입니다.
- `ecosystem` 파라미터를 사용하여 npm, pip, apt 생태계별로 데이터가 격리됩니다.
- `force=true`로 요청 시 기존 분석 결과를 삭제하고 재분석을 트리거합니다.

### 오류 응답
모든 오류는 표준화된 JSON 봉투 형식을 따릅니다:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "사람이 읽을 수 있는 오류 메시지",
    "details": {},
    "request_id": "f3f8c83e-..."
  }
}
```

**주요 오류 코드:**
- `INVALID_INPUT` (400): 누락되거나 유효하지 않은 쿼리 파라미터
- `RESOURCE_NOT_FOUND` (404): 데이터베이스에서 데이터를 찾을 수 없음
- `ANALYSIS_IN_PROGRESS` (202): 분석이 시작되어 처리 중
- `EXTERNAL_SERVICE_ERROR` (503): 데이터베이스 또는 캐시 사용 불가
- `INTERNAL_ERROR` (500): 예상치 못한 서버 오류

**HTTP 상태 코드:**
- `200`: 성공
- `202`: 수락됨 (분석 진행 중)
- `400`: 잘못된 요청 (유효하지 않은 파라미터)
- `401`: 인증되지 않음 (API 키 누락)
- `403`: 금지됨 (유효하지 않은 API 키)
- `404`: 찾을 수 없음
- `429`: 요청 제한 초과 (rate limit)
- `500`: 내부 서버 오류
- `503`: 서비스 사용 불가
