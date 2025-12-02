# API 명세서 (API Specification)

**문서 버전**: 2.0  
**최종 업데이트**: 2025-12-01  
**대상 독자**: 개발팀, 아키텍트, 기술 의사결정자

---

## 목차
1. [시스템 개요](#1-시스템-개요)
2. [아키텍처 특징](#2-아키텍처-특징)
3. [인증 및 보안](#3-인증-및-보안)
4. [내부 서비스 API](#4-내부-서비스-api)
5. [외부 노출 API (QueryAPI)](#5-외부-노출-api-queryapi)
6. [에러 처리 및 복구](#6-에러-처리-및-복구)
7. [성능 최적화](#7-성능-최적화)
8. [통합 사용 시나리오](#8-통합-사용-시나리오)

---

## 1. 시스템 개요

### 1.1 아키텍처 철학

본 시스템은 **Microservice 아키텍처**를 채택하여 다음과 같은 장점을 확보했다:

| 설계 원칙 | 구현 방법 | 기술적 이점 |
|----------|-----------|-----------|
| **Single Responsibility** | 각 서비스가 하나의 역할만 담당 | 독립적 배포, 장애 격리 |
| **Loose Coupling** | REST API를 통한 서비스 간 통신 | 기술 스택 유연성 |
| **Fault Isolation** | 서비스별 독립 실행 | 부분 장애 시에도 전체 시스템 동작 |
| **Horizontal Scalability** | Stateless 설계 | 부하에 따라 개별 서비스 스케일링 가능 |

### 1.2 서비스 구성도

```
┌──────────────────────────────────────────────────────────────┐
│                        Client Layer                          │
│  (Web Dashboard, CLI, External API Consumers)                │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                      QueryAPI (Port 8004)                     │
│  [Authentication, Rate Limiting, Caching, Response Envelope]  │
└──────┬───────────────────────────────────────────┬───────────┘
       │                                           │
       ▼                                           ▼
┌─────────────────────┐                   ┌─────────────────────┐
│   Redis Cache       │                   │   PostgreSQL DB     │
│  (Sub-second Query) │                   │  (Persistent Data)  │
└─────────────────────┘                   └─────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
┌─────────────────────┐         ┌─────────────────────┐
│  Agent Orchestrator │         │   Worker Processes  │
│    (CLI/Main Loop)  │         │  (Background Queue) │
└───────┬─────────────┘         └─────────────────────┘
        │
        │ Calls Internal APIs in sequence:
        │
        ├──► MappingCollector (8000) → CVE 수집
        ├──► CVSSFetcher (8006) ─┐
        ├──► EPSSFetcher (8001) ─┤ → 점수 수집 (병렬)
        ├──► ThreatAgent (8002)    → 위협 정보
        └──► Analyzer (8003)        → 최종 분석
```

### 1.3 데이터 플로우

`lodash` 패키지 분석 플로우:

```
1. Client Request
   └─> GET /api/v1/query?package=lodash&version=latest
   
2. QueryAPI Processing
   ├─> Check Redis Cache (키: query:npm:lodash:latest)
   │   └─> Cache Hit → 즉시 반환 (< 100ms)
   │   └─> Cache Miss → 계속
   │
   ├─> Check PostgreSQL
   │   └─> Data Exists → 캐시 갱신 후 반환
   │   └─> Data Missing → 분석 작업 생성
   │
   └─> Submit to Redis Queue (analysis_tasks)
       └─> Return 202 ACCEPTED + "분석 진행 중" 메시지

3. Background Worker Processing
   ├─> MappingCollector: lodash → [CVE-2023-1234, CVE-2023-5678]
   ├─> CVSSFetcher: CVE-2023-1234 → CVSS 9.8
   ├─> EPSSFetcher: CVE-2023-1234 → EPSS 0.87
   ├─> ThreatAgent: 실제 공격 사례 검색
   └─> Analyzer: 종합 분석 + AI 리포트 생성

4. Client Polling
   └─> 5초마다 재요청 → 분석 완료 시 200 OK 반환
```

---

## 2. 아키텍처 특징

### 2.1 왜 Microservice인가?

**기술적 배경:**

현대적인 보안 분석 시스템은 다음과 같은 특성을 가진다:
- **외부 API 의존성**: NVD, FIRST.org, AI 모델 등 다양한 외부 서비스
- **처리 시간 편차**: CVE 조회(1초) vs AI 분석(60초+)
- **확장성 요구**: 특정 서비스만 집중적 부하 발생 가능

**Monolithic 아키텍처의 한계:**
```
┌────────────────────────────────┐
│    Single Process App         │
│  ┌──────────────────────────┐ │
│  │  All Services Combined   │ │  ← 하나의 서비스 장애가
│  │  (CVE + AI + DB + Cache) │ │    전체 시스템 중단
│  └──────────────────────────┘ │
└────────────────────────────────┘
     ↓ AI 분석 CPU 100% ↓
   전체 시스템 응답 없음
```

**Microservice 아키텍처의 해결:**
```
Service A (Fast)    Service B (Slow)    Service C (Fast)
   ┌─────┐             ┌─────┐            ┌─────┐
   │ CVE │ ← 정상      │ AI  │ ← 부하     │Cache│ ← 정상
   └─────┘             └─────┘            └─────┘
     ↓                   ↓ CPU 100%          ↓
   정상 동작           Scale Up!          정상 동작
```

### 2.2 비동기 처리 전략

**문제**: CVE 분석은 60-120초가 소요되어 HTTP 타임아웃 발생

**해결**: Event-Driven Architecture

```python
# 기존 동기 처리 (문제)
def analyze_sync(package):
    result = long_running_analysis(package)  # 120초 대기
    return result  # 타임아웃!

# 개선된 비동기 처리
def analyze_async(package):
    job_id = submit_to_queue(package)  # 즉시 반환
    return {"status": "processing", "job_id": job_id}
    
# 클라이언트는 폴링으로 결과 확인
def check_result(job_id):
    return get_from_db(job_id)  # 완료되면 결과 반환
```

### 2.3 캐싱 전략 (3-Tier)

**계층별 캐싱으로 성능 극대화:**

```
Layer 1: In-Memory Cache (Python dict)
├─ 속도: < 1ms
├─ 용량: 제한적 (수백 MB)
└─ 용도: 단일 프로세스 내 재사용

Layer 2: Redis Cache
├─ 속도: 1-5ms (네트워크 포함)
├─ 용량: 수 GB
├─ TTL: 기본 3600초
└─ 용도: 서비스 간 공유 데이터

Layer 3: PostgreSQL
├─ 속도: 10-50ms (인덱스 사용 시)
├─ 용량: 무제한
└─ 용도: 영구 저장 및 복잡한 쿼리
```

**캐시 키 네이밍 컨벤션:**
```
패턴: {서비스}:{생태계}:{식별자}:{버전}

예시:
- mapping:npm:lodash:latest
- cvss:CVE-2023-1234
- epss:CVE-2023-1234
- analysis:npm:lodash:latest:CVE-2023-1234
```

---

## 3. 인증 및 보안

### 3.1 API Key 기반 인증

API Key를 선택한 이유:
- OAuth보다 구현이 훨씬 간단함
- 내부 시스템 간 통신엔 이 정도면 충분
- 나중에 JWT로 갈아타기도 쉬움

**구현:**

```python
# 설정 (.env)
NT_QUERY_API_KEYS=dev-key-123,prod-key-456,admin-key-789

# 검증 로직 (query_api/app/auth.py)
async def verify_api_key(api_key: str) -> bool:
    valid_keys = os.getenv("NT_QUERY_API_KEYS", "").split(",")
    return api_key in valid_keys

# FastAPI 미들웨어
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/v1"):
        api_key = request.headers.get("X-API-Key")
        if not await verify_api_key(api_key):
            return JSONResponse(
                status_code=401,
                content={"error": {"code": "UNAUTHORIZED", "message": "Invalid API key"}}
            )
    return await call_next(request)
```

**사용 예시:**

```bash
# 성공 케이스
curl -H "X-API-Key: dev-key-123" \
     http://localhost:8004/api/v1/query?package=lodash

# 실패 케이스 (401)
curl http://localhost:8004/api/v1/query?package=lodash
```

### 3.2 Rate Limiting

**목적**: DoS 공격 방지 및 공정한 리소스 사용

**구현**: `slowapi` 라이브러리 사용

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# 적용 예시
@app.get("/api/v1/query")
@limiter.limit("5/minute")  # 분당 5회 제한
async def query_package(package: str):
    # ...

# Rate limit 초과 시 응답
HTTP/1.1 429 Too Many Requests
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded: 5 per 1 minute",
    "retry_after": 42
  }
}
```

**엔드포인트별 제한:**

| 엔드포인트 | 제한 | 이유 |
|-----------|------|------|
| `/api/v1/query` | 5/분 | 분석 비용이 높음 (AI 사용) |
| `/api/v1/history` | 10/분 | DB 조회만 수행 |
| `/api/v1/stats` | 5/분 | 집계 쿼리로 부하 |

### 3.3 Request ID 추적

**목적**: 분산 시스템에서 요청 추적 및 디버깅

```python
# 미들웨어 (common_lib/observability.py)
import uuid

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    
    # 컨텍스트에 저장
    request.state.request_id = request_id
    
    # 로깅에 포함
    logger.info(f"[{request_id}] {request.method} {request.url.path}")
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response
```

**사용 시나리오:**

```bash
# 요청
curl -H "X-Request-ID: debug-session-001" \
     http://localhost:8004/api/v1/query?package=lodash

# 응답 헤더
X-Request-ID: debug-session-001

# 로그에서 추적
grep "debug-session-001" /var/log/app.log
```

---

## 4. 내부 서비스 API

### 4.1 MappingCollector (Port 8000)

**역할**: 패키지명 → CVE ID 매핑

**엔드포인트**: `POST /collect`

#### 요청

```json
{
  "package": "lodash",
  "version_range": "<4.17.21",
  "collected_at": "2025-12-01T12:34:56Z"
}
```

#### 응답

```json
{
  "package": "lodash",
  "version_range": "<4.17.21",
  "cve_ids": ["CVE-2023-1234", "CVE-2023-5678"],
  "collected_at": "2025-12-01T12:34:56Z"
}
```

#### 내부 로직

```python
async def fetch_cves(package: str, version_range: str) -> List[str]:
    # 1차: Perplexity AI로 검색
    try:
        cves = await perplexity_search(f"{package} CVE vulnerability")
        if cves:
            return normalize_cve_ids(cves)
    except Exception as e:
        logger.warning(f"Perplexity search failed: {e}")
    
    # 2차 폴백: NVD Feed 직접 조회
    return await nvd_feed_query(package, version_range)
```

#### 오류 처리

| HTTP Code | 오류 코드 | 설명 | 조치 |
|-----------|----------|------|------|
| 400 | `INVALID_INPUT` | 패키지명 누락 또는 형식 오류 | 요청 수정 |
| 500 | `INTERNAL_ERROR` | 서버 오류 | 재시도 (Exponential Backoff) |
| 502 | `EXTERNAL_SERVICE_ERROR` | Perplexity/NVD API 장애 | 폴백 데이터 사용 |

---

### 4.2 CVSSFetcher (Port 8006)

**역할**: CVE → CVSS 점수 수집

**엔드포인트**: `POST /api/v1/cvss`

#### 요청

```json
{
  "cve_id": "CVE-2023-1234"
}
```

#### 응답

```json
{
  "cve_id": "CVE-2023-1234",
  "cvss_score": 9.8,
  "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
  "severity": "CRITICAL",
  "collected_at": "2025-12-01T12:34:56Z"
}
```

#### CVSS Vector 해석

```
CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H
         ────  ────  ────  ────  ──  ──  ──  ──
          │     │     │     │    │   │   │   └─ Availability: High
          │     │     │     │    │   │   └───── Integrity: High
          │     │     │     │    │   └────────── Confidentiality: High
          │     │     │     │    └──────────────── Scope: Unchanged
          │     │     │     └────────────────────── User Interaction: None
          │     │     └───────────────────────────── Privileges Required: None
          │     └──────────────────────────────────── Attack Complexity: Low
          └─────────────────────────────────────────── Attack Vector: Network

해석: 원격에서 인증 없이 쉽게 공격 가능하며, 기밀성/무결성/가용성 모두 침해 → CRITICAL
```

---

### 4.3 EPSSFetcher (Port 8001)

**역할**: CVE → EPSS 확률 수집

**엔드포인트**: `POST /api/v1/epss`

#### 요청

```json
{
  "cve_id": "CVE-2023-1234"
}
```

#### 응답

```json
{
  "cve_id": "CVE-2023-1234",
  "epss_score": 0.87,
  "percentile": 0.95,
  "collected_at": "2025-12-01T12:34:56Z"
}
```

#### EPSS 점수 해석

| EPSS 범위 | 의미 | 조치 우선순위 |
|-----------|------|--------------|
| 0.9 - 1.0 | 매우 높은 확률 (90%+) | 즉시 패치 |
| 0.5 - 0.9 | 높은 확률 | 24시간 내 패치 |
| 0.1 - 0.5 | 중간 확률 | 1주일 내 패치 |
| 0.0 - 0.1 | 낮은 확률 | 모니터링 |

**실제 예시:**
```
CVE-2023-1234: EPSS = 0.87 (87%)
  → 향후 30일 내 실제 공격에 사용될 확률이 87%
  → Kenna Security 데이터 기반 예측
```

---

### 4.4 ThreatAgent (Port 8002)

**역할**: 실제 공격 사례 수집 (AI 기반)

**엔드포인트**: `POST /threats`

#### 요청

```json
{
  "cve_id": "CVE-2023-1234",
  "package": "lodash",
  "version_range": "<4.17.21"
}
```

#### 응답

```json
{
  "cve_id": "CVE-2023-1234",
  "package": "lodash",
  "version_range": "<4.17.21",
  "cases": [
    {
      "source": "https://example.com/exploit-detail",
      "title": "Exploitation of CVE-2023-1234 in lodash",
      "date": "2025-11-20",
      "summary": "Attackers chained this vulnerability with SQL injection to gain RCE on production servers. Observed in APT29 campaigns targeting financial institutions.",
      "collected_at": "2025-12-01T12:40:00Z"
    }
  ]
}
```

#### 내부 파이프라인

```
1. Perplexity Search
   └─> Query: "CVE-2023-1234 lodash exploit POC attack in-the-wild"
   
2. Claude Summarization
   └─> Prompt: "Summarize real-world exploitation of CVE-2023-1234"
   
3. Sanitization
   ├─> HTML Tag Removal
   ├─> Control Character Removal
   ├─> URL Validation (http/https only)
   └─> Length Limit (title: 256, summary: 2048)
   
4. JSONB Serialization
   └─> Store in PostgreSQL as structured data
```

#### Sanitization 예시

```python
# Before
raw_summary = "<script>alert('xss')</script>Attackers used\x00\x01..."

# After
clean_summary = "Attackers used..."
```

---

### 4.5 Analyzer (Port 8003)

**역할**: 종합 분석 및 AI 리포트 생성

**엔드포인트**: `POST /analyze`

#### 요청

```json
{
  "cve_id": "CVE-2023-1234",
  "epss_score": 0.87,
  "cvss_score": 9.8,
  "cases": [
    {
      "title": "Real exploit case",
      "summary": "..."
    }
  ],
  "package": "lodash",
  "version_range": "<4.17.21"
}
```

#### 응답

```json
{
  "cve_id": "CVE-2023-1234",
  "risk_level": "CRITICAL",
  "risk_score": 92.3,
  "recommendations": [
    "즉시 lodash를 4.17.21 이상으로 업그레이드하세요 (npm update lodash@^4.17.21).",
    "WAF 룰을 추가하여 익스플로잇 패턴을 차단하세요.",
    "영향받는 서비스의 로그를 분석하여 침해 여부를 확인하세요."
  ],
  "analysis_summary": "## lodash CVE-2023-1234 분석\n\n### 취약점 개요\nPrototype Pollution 취약점으로...",
  "generated_at": "2025-12-01T12:42:00Z"
}
```

#### Risk Score 계산식

```python
# 가중치 기반 점수 계산
def calculate_risk_score(cvss, epss, ai_level):
    AI_SCORE_MAP = {
        "CRITICAL": 9.5,
        "HIGH": 7.5,
        "MEDIUM": 5.0,
        "LOW": 2.0
    }
    
    cvss_weighted = cvss * 0.4          # 40% 가중치
    epss_weighted = (epss * 10) * 0.3    # 30% 가중치 (0-1 → 0-10 스케일)
    ai_weighted = AI_SCORE_MAP[ai_level] * 0.3  # 30% 가중치
    
    return cvss_weighted + epss_weighted + ai_weighted

# 예시
risk_score = calculate_risk_score(9.8, 0.87, "CRITICAL")
# = (9.8 * 0.4) + (8.7 * 0.3) + (9.5 * 0.3)
# = 3.92 + 2.61 + 2.85
# = 9.38 → P1 (Critical)
```

---

## 5. 외부 노출 API (QueryAPI)

### 5.1 설계 원칙

**QueryAPI는 내부 복잡성을 숨기고 간단한 인터페이스를 제공:**

```
Client Perspective (Simple)
│
├─> GET /api/v1/query?package=lodash
│
└─> Response: { "cve_list": [...] }

Backend Reality (Complex)
│
├─> Redis Cache Check
├─> PostgreSQL Query
├─> Job Queue Submission
├─> Worker Processing (6 services)
└─> Response Aggregation
```

### 5.2 인증

**모든 QueryAPI 엔드포인트는 `X-API-Key` 헤더 필수:**

```bash
# 기본 사용
curl -H "X-API-Key: dev-api-key-123" \
     "http://localhost:8004/api/v1/query?package=lodash"
```

**환경 변수 설정:**

```bash
# .env
NT_QUERY_API_KEYS=dev-key-123,prod-key-456

# Docker Compose
environment:
  - NT_QUERY_API_KEYS=${NT_QUERY_API_KEYS}
```

### 5.3 GET /api/v1/query

**가장 중요한 엔드포인트 - 패키지 또는 CVE 조회**

#### 파라미터

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---------|------|------|--------|------|
| `package` | string | ○* | - | 패키지명 (예: "lodash") |
| `cve_id` | string | ○* | - | CVE ID (예: "CVE-2023-1234") |
| `version` | string | ✗ | "latest" | 패키지 버전 |
| `ecosystem` | string | ✗ | "npm" | 생태계 (npm/pip/apt) |
| `force` | boolean | ✗ | false | 강제 재분석 |

*`package`와 `cve_id` 중 하나는 필수

#### 응답 (200 OK)

```json
{
  "package": "lodash",
  "version": "latest",
  "ecosystem": "npm",
  "cve_list": [
    {
      "cve_id": "CVE-2023-1234",
      "cvss_score": 9.8,
      "epss_score": 0.87,
      "risk_level": "CRITICAL",
      "risk_score": 92.3,
      "risk_label": "P1",
      "analysis_summary": "## 취약점 분석\n...",
      "recommendations": [
        "즉시 패치 적용: npm update lodash@^4.17.21"
      ],
      "threat_cases": [
        {
          "title": "APT29 exploitation",
          "date": "2025-11-20",
          "summary": "..."
        }
      ]
    }
  ],
  "metadata": {
    "total_cves": 1,
    "scan_timestamp": "2025-12-01T12:42:00Z",
    "cache_hit": true
  }
}
```

#### 응답 (202 Accepted - 분석 진행 중)

```json
{
  "status": "ANALYSIS_IN_PROGRESS",
  "message": "분석이 시작되었습니다. 30-120초 후 다시 요청하세요.",
  "job_id": "analysis-123e4567-e89b",
  "estimated_completion": "2025-12-01T12:44:00Z",
  "retry_after": 30
}
```

#### 사용 시나리오

**시나리오 1: 신규 패키지 조회 (캐시 미스)**

```bash
# 1차 요청
curl -H "X-API-Key: dev-key-123" \
     "http://localhost:8004/api/v1/query?package=express&version=4.17.1"

# 응답: 202 Accepted
{
  "status": "ANALYSIS_IN_PROGRESS",
  "retry_after": 30
}

# 30초 대기 후 재요청
sleep 30
curl -H "X-API-Key: dev-key-123" \
     "http://localhost:8004/api/v1/query?package=express&version=4.17.1"

# 응답: 200 OK (분석 완료)
{
  "package": "express",
  "cve_list": [...]
}
```

**시나리오 2: 강제 재분석 (force=true)**

```bash
# 기존 데이터 무시하고 재분석
curl -H "X-API-Key: dev-key-123" \
     "http://localhost:8004/api/v1/query?package=lodash&force=true"

# 시스템 동작:
# 1. Redis 캐시 삭제
# 2. PostgreSQL 레코드 삭제
# 3. 새 분석 작업 생성
# 4. 202 Accepted 반환
```

**시나리오 3: 멀티 에코시스템**

```bash
# npm 패키지
curl "http://localhost:8004/api/v1/query?package=lodash&ecosystem=npm"

# Python 패키지
curl "http://localhost:8004/api/v1/query?package=django&ecosystem=pip"

# 데이터 격리: npm의 lodash ≠ pip의 lodash (서로 다른 저장소)
```

---

### 5.4 GET /api/v1/history

**과거 분석 기록 조회 (페이지네이션)**

#### 파라미터

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---------|------|------|--------|------|
| `skip` | integer | ✗ | 0 | 건너뛸 레코드 수 |
| `limit` | integer | ✗ | 10 | 반환할 레코드 수 (최대 100) |
| `ecosystem` | string | ✗ | "npm" | 생태계 필터 |

#### 응답

```json
{
  "skip": 0,
  "limit": 10,
  "total_returned": 3,
  "records": [
    {
      "cve_id": "CVE-2023-1234",
      "package": "lodash",
      "version": "latest",
      "ecosystem": "npm",
      "risk_level": "CRITICAL",
      "risk_score": 92.3,
      "generated_at": "2025-12-01T12:42:00Z",
      "created_at": "2025-12-01T12:42:00Z"
    }
  ]
}
```

#### 페이지네이션 예시

```bash
# 1페이지 (0-9)
curl "http://localhost:8004/api/v1/history?skip=0&limit=10"

# 2페이지 (10-19)
curl "http://localhost:8004/api/v1/history?skip=10&limit=10"

# 3페이지 (20-29)
curl "http://localhost:8004/api/v1/history?skip=20&limit=10"
```

---

### 5.5 GET /api/v1/stats

**위험도 분포 통계**

#### 응답

```json
{
  "total_scans": 250,
  "ecosystem": "npm",
  "risk_distribution": {
    "CRITICAL": 15,
    "HIGH": 45,
    "MEDIUM": 120,
    "LOW": 60,
    "UNKNOWN": 10
  },
  "last_updated": "2025-12-01T12:00:00Z"
}
```

#### 대시보드 활용

```javascript
// React Component
const StatsCard = ({ stats }) => {
  const total = stats.total_scans;
  const critical = stats.risk_distribution.CRITICAL;
  const criticalPercent = (critical / total * 100).toFixed(1);
  
  return (
    <div className="stat-card">
      <h3>Critical Alerts</h3>
      <p className="number">{critical}</p>
      <p className="percent">{criticalPercent}% of total</p>
    </div>
  );
};
```

---

## 6. 에러 처리 및 복구

### 6.1 표준 에러 봉투

**모든 에러는 동일한 JSON 구조:**

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "사람이 읽을 수 있는 설명",
    "details": {
      "field_errors": {},
      "recovery_suggestions": []
    },
    "request_id": "f3f8c83e-1234-5678-9abc-def012345678",
    "timestamp": "2025-12-01T12:42:00Z"
  }
}
```

### 6.2 에러 코드 레퍼런스

| HTTP | 에러 코드 | 의미 | 복구 방법 |
|------|----------|------|----------|
| 400 | `INVALID_INPUT` | 파라미터 누락/형식 오류 | 요청 수정 |
| 401 | `UNAUTHORIZED` | API 키 누락 | `X-API-Key` 헤더 추가 |
| 403 | `FORBIDDEN` | 유효하지 않은 API 키 | 올바른 키 사용 |
| 404 | `RESOURCE_NOT_FOUND` | 데이터 미존재 | 다른 패키지 조회 |
| 429 | `RATE_LIMIT_EXCEEDED` | 속도 제한 초과 | Retry-After 헤더 확인 후 대기 |
| 500 | `INTERNAL_ERROR` | 서버 내부 오류 | 재시도 또는 관리자 문의 |
| 502 | `EXTERNAL_SERVICE_ERROR` | 외부 API 장애 | 폴백 데이터 사용 또는 재시도 |
| 503 | `SERVICE_UNAVAILABLE` | DB/Redis 사용 불가 | 시스템 복구 대기 |

### 6.3 재시도 전략

**권장 재시도 로직 (Exponential Backoff):**

```python
import time

def exponential_backoff_retry(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            logger.warning(f"Retry {attempt + 1}/{max_retries} after {wait_time}s")
            time.sleep(wait_time)

# 사용 예시
result = exponential_backoff_retry(lambda: call_api())
```

**재시도 대상:**
- ✅ 502, 503, 504 (일시적 장애)
- ✅ 429 (Rate Limit) - 단, Retry-After 준수
- ✅ 네트워크 타임아웃
- ❌ 400, 401, 403, 404 (클라이언트 오류 - 재시도 무의미)

---

## 7. 성능 최적화

### 7.1 캐시 히트율

**측정 기준:**
```
Cache Hit Rate = (Redis Hits) / (Total Requests) × 100%

목표: 80% 이상
```

**개선 방법:**
- TTL 조정 (기본 3600초 → 상황에 따라 증가)
- 인기 패키지 Pre-warming
- Cache Stampede 방지 (Cache Lock)

### 7.2 응답 시간 SLA

| 시나리오 | 목표 응답 시간 | 실제 측정 |
|---------|--------------|----------|
| Cache Hit | < 100ms | ~50ms |
| DB Query | < 500ms | ~200ms |
| 신규 분석 (비동기) | 60-120s | ~90s (평균) |

### 7.3 부하 테스트 결과

```bash
# Locust 부하 테스트
locust -f loadtest.py --host=http://localhost:8004

# 결과 (4 Core, 8GB RAM)
- 동시 사용자: 100명
- RPS: 250 req/s (캐시 히트)
- 평균 응답: 45ms
- 99th percentile: 120ms
- 에러율: 0.1%
```

---

## 8. 통합 사용 시나리오

### 8.1 End-to-End 예시: CI/CD 통합

```yaml
# .github/workflows/security-scan.yml
name: Dependency Security Scan

on:
  pull_request:
    paths:
      - 'package.json'
      - 'package-lock.json'

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Extract dependencies
        id: deps
        run: |
          npm list --depth=0 --json > deps.json
          
      - name: Scan with QueryAPI
        env:
          API_KEY: ${{ secrets.QUERYAPI_KEY }}
        run: |
          for pkg in $(jq -r '.dependencies | keys[]' deps.json); do
            response=$(curl -s -H "X-API-Key: $API_KEY" \
              "http://api.example.com/api/v1/query?package=$pkg")
            
            # P1 (Critical) 발견 시 빌드 실패
            p1_count=$(echo $response | jq '[.cve_list[] | select(.risk_label == "P1")] | length')
            if [ $p1_count -gt 0 ]; then
              echo "❌ Critical vulnerability found in $pkg"
              exit 1
            fi
          done
```

### 8.2 대시보드 통합

```typescript
// React Query 사용 예시
import { useQuery } from '@tanstack/react-query';

function PackageScanner() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['package', packageName],
    queryFn: async () => {
      const response = await fetch(
        `${API_URL}/api/v1/query?package=${packageName}`,
        {
          headers: {
            'X-API-Key': API_KEY,
            'X-Request-ID': generateRequestId()
          }
        }
      );
      
      if (response.status === 202) {
        // 분석 진행 중 - 5초 후 재시도
        throw new Error('ANALYSIS_IN_PROGRESS');
      }
      
      return response.json();
    },
    retry: 6, // 총 30초 동안 재시도
    retryDelay: 5000 // 5초 간격
  });
  
  if (isLoading) return <Spinner />;
  if (error?.message === 'ANALYSIS_IN_PROGRESS') {
    return <AnalysisPendingBanner />;
  }
  
  return <CVEList cves={data.cve_list} />;
}
```

---

## 부록 A: 전체 API 엔드포인트 매트릭스

| 서비스 | 엔드포인트 | 메서드 | 포트 | 인증 | Rate Limit | 용도 |
|--------|-----------|--------|------|------|-----------|------|
| MappingCollector | `/collect` | POST | 8000 | ❌ | - | 내부: CVE 수집 |
| CVSSFetcher | `/api/v1/cvss` | POST | 8006 | ❌ | - | 내부: CVSS 조회 |
| EPSSFetcher | `/api/v1/epss` | POST | 8001 | ❌ | - | 내부: EPSS 조회 |
| ThreatAgent | `/threats` | POST | 8002 | ❌ | - | 내부: 위협 수집 |
| Analyzer | `/analyze` | POST | 8003 | ❌ | - | 내부: 분석 |
| QueryAPI | `/api/v1/query` | GET | 8004 | ✅ | 5/분 | 외부: 조회 |
| QueryAPI | `/api/v1/history` | GET | 8004 | ✅ | 10/분 | 외부: 히스토리 |
| QueryAPI | `/api/v1/stats` | GET | 8004 | ✅ | 5/분 | 외부: 통계 |
| QueryAPI | `/health` | GET | 8004 | ❌ | - | 헬스체크 |

---

**문서 마지막 업데이트**: 2025-12-01  
**문서 버전**: 2.0  
**다음 리뷰 예정**: 2026-01-01
