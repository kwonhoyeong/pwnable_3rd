# 검증 가이드 (Verification Guide)

이 가이드는 주요 리팩토링 스프린트 수정 사항에 대한 수동 검증 단계를 제공합니다.

---

## 🧪 자동화된 테스트 (Automated Tests)

### 회귀 테스트 실행 (Running Regression Tests)

```bash
# pytest가 설치되지 않은 경우 설치
pip install pytest pytest-asyncio httpx

# 모든 회귀 테스트 실행
pytest tests/test_regression.py -v

# 특정 테스트 실행
pytest tests/test_regression.py::test_api_auth_with_valid_key_returns_200 -v
```

**예상 결과:**
- ✅ 모든 테스트 통과
- ✅ API 인증 테스트: 키 없이 401/403, 키 있으면 200 확인
- ✅ Stats 엔드포인트: UPPERCASE 키 반환 확인 (CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN)
- ✅ CVSS fetcher 단위 테스트: NVD 우선 전략 및 Perplexity 폴백 확인

---

## 🔐 수동 검증: API 키 인증 (API Key Authentication)

### 테스트 1: API 키 없이 요청

```bash
curl -X GET http://localhost:8004/api/v1/stats
```

**예상 결과:** API 키 누락에 대한 오류 메시지와 함께 HTTP 401/403

### 테스트 2: 유효한 API 키로 요청

```bash
curl -X GET http://localhost:8004/api/v1/stats \
  -H "X-API-Key: dev-api-key-123"
```

**예상 결과:** 유효한 JSON 응답과 함께 HTTP 200

---

## 📊 수동 검증: Stats 엔드포인트 UPPERCASE 키

### 테스트: Stats 응답 스키마 확인

```bash
curl -X GET http://localhost:8004/api/v1/stats \
  -H "X-API-Key: dev-api-key-123" | jq .
```

**예상 출력 구조:**
```json
{
  "total_scans": 123,
  "risk_distribution": {
    "CRITICAL": 5,
    "HIGH": 12,
    "MEDIUM": 45,
    "LOW": 61,
    "UNKNOWN": 0
  }
}
```

**✅ 확인 사항:**
- `risk_distribution`의 모든 키가 **대문자(UPPERCASE)**
- "Unknown"과 같은 혼합 대소문자 키가 없음
- 모든 값이 정수형

---

## 🔄 수동 검증: Worker Dead Letter Queue (DLQ)

### 테스트 1: 작업 실패 트리거

**옵션 A: 처리 오류 시뮬레이션**

1. **Worker를 임시로 수정** (또는 테스트 작업 주입):
   ```python
   # worker.py의 process_task 함수에 추가:
   if package == "test-fail-package":
       raise Exception("DLQ 테스트용 의도적 실패")
   ```

2. **테스트 작업 제출:**
   ```bash
   docker exec npm-threat-redis redis-cli RPUSH analysis_tasks '{"package":"test-fail-package","version":"latest"}'
   ```

**옵션 B: 잘못된 형식의 작업 제출**

```bash
# 유효하지 않은 JSON 작업 제출
docker exec npm-threat-redis redis-cli RPUSH analysis_tasks '{"invalid_task_structure":true}'
```

### 테스트 2: DLQ 확인

```bash
# DLQ 길이 확인
docker exec npm-threat-redis redis-cli LLEN analysis_tasks:failed

# 실패한 작업 조회
docker exec npm-threat-redis redis-cli LRANGE analysis_tasks:failed 0 -1
```

**예상 결과:**
- DLQ 길이 > 0
- 실패한 작업 페이로드에 포함되어야 할 항목:
  - 원본 작업 데이터
  - 예외 메시지가 포함된 `error_msg` 필드
  - `error_timestamp` 필드
  - `error_traceback` 필드 (선택 사항)

### 테스트 3: Worker 계속 실행 확인

```bash
# Worker 로그 확인
docker logs npm-threat-agent-orchestrator --tail 50

# Worker가 여전히 실행 중이며 다음 작업 준비 완료
docker exec npm-threat-redis redis-cli RPUSH analysis_tasks '{"package":"react","version":"latest"}'
```

**예상 결과:**
- Worker 로그에 "💀 Task failed and will be moved to DLQ" 표시
- Worker 로그에 "📮 Failed task pushed to DLQ" 표시
- Worker가 후속 작업을 계속 처리
- Worker 충돌이나 종료 없음

### 테스트 4: Redis 연결 복원력 검증

```bash
# Worker 실행 중에 Redis 재시작
docker restart npm-threat-redis

# 10초 대기 후 Worker 로그 확인
docker logs npm-threat-agent-orchestrator --tail 20
```

**예상 결과:**
- Worker 로그에 "Redis connection error" 표시
- Worker 로그에 "Attempting to reconnect to Redis" 표시
- Worker 로그에 "✅ Redis connection restored" 표시
- Worker가 수동 재시작 없이 처리 재개

---

## ♻️ 수동 검증: Force 재분석 & 다중 에코시스템

### 테스트 1: pip 생태계 데이터 격리

```bash
curl -X GET "http://localhost:8004/api/v1/query?package=requests&version=latest&ecosystem=pip" \
  -H "X-API-Key: dev-api-key-123"
```

**예상 결과:**  
- `package`는 `requests`, `cve_list`는 pip 생태계 결과만 포함  
- `risk_label`/`risk_score`가 응답에 존재  
- 같은 패키지 이름을 npm으로 조회하면(아래 테스트) 서로 다른 결과를 반환

```bash
curl -X GET "http://localhost:8004/api/v1/query?package=requests&version=latest&ecosystem=npm" \
  -H "X-API-Key: dev-api-key-123"
```

**예상 결과:** npm 생태계 결과가 없으면 `RESOURCE_NOT_FOUND` 또는 `ANALYSIS_IN_PROGRESS`, pip 데이터가 섞여서 반환되지 않음.

### 테스트 2: force=true 재분석 흐름

1. **기존 데이터 확보**
   ```bash
   curl -X GET "http://localhost:8004/api/v1/query?package=lodash&version=latest&ecosystem=npm" \
     -H "X-API-Key: dev-api-key-123"
   ```

2. **Force 재분석 트리거**
   ```bash
   curl -X GET "http://localhost:8004/api/v1/query?package=lodash&version=latest&ecosystem=npm&force=true" \
     -H "X-API-Key: dev-api-key-123"
   ```

   **예상 결과:**  
   - HTTP 202(`ANALYSIS_IN_PROGRESS`) 또는 새 결과(HTTP 200)  
   - Redis 큐에 작업 1건 추가 (`redis-cli LLEN analysis_tasks`)

3. **DLQ/작업 큐 확인**
   ```bash
   docker exec npm-threat-redis redis-cli LLEN analysis_tasks
   docker exec npm-threat-redis redis-cli LLEN analysis_tasks:failed
   ```

4. **재분석 완료 확인**  
   force 호출 후 1~2분 내 동일 요청을 재시도하여 `generated_at` 혹은 `risk_score`가 갱신되었는지 확인합니다.

**검증 포인트:**  
- Force 호출이 다른 버전/생태계 레코드를 삭제하지 않음  
- `analysis_tasks` 큐에 `ecosystem":"npm"` 필드 포함  
- 재분석 중에는 QueryAPI가 `AnalysisInProgressError`를 반환함

---

## 🌐 수동 검증: 프론트엔드 대시보드

### 테스트 1: 대시보드가 오류 없이 로드됨

1. **브라우저 열기**: `http://localhost:5173` 이동
2. **DevTools 열기**: F12를 누르고 Console 탭 확인
3. **대시보드 로드 대기**

**예상 결과:**
- ✅ 빈 화면 없이 대시보드 표시
- ✅ 콘솔 오류 없음 (특히 "VITE_QUERY_API_KEY missing" 오류 없음)
- ✅ Stats 카드에 숫자 표시 (Total Scans, Critical, High, Medium 개수)
- ✅ "Recent Vulnerability Reports" 테이블 로드

### 테스트 2: 검색 기능

1. **패키지 이름 입력**: 검색 바에 "react" 입력
2. **검색 제출**
3. **결과 대기**

**예상 결과:**
- ✅ 로딩 인디케이터 표시
- ✅ 2분 이내에 결과 표시 (또는 "Analysis in progress" 메시지)
- ✅ 콘솔에 401/403 인증 오류 없음
- ✅ CVE 클릭 시 보고서 상세 페이지 로드

### 테스트 3: Stats 카드가 올바르게 표시됨

**확인 사항:**
- ✅ "Total Scans" 카드에 숫자 표시
- ✅ "Critical", "High", "Medium" 카드에 숫자 표시
- ✅ 숫자가 "undefined"나 "NaN"이 아님

---

## 🔍 수동 검증: CVSS Fetcher NVD 통합

### 테스트: 로그에서 CVSS 소스 확인

```bash
# 새 패키지 스캔 트리거
curl -X GET "http://localhost:8004/api/v1/query?package=lodash&version=latest" \
  -H "X-API-Key: dev-api-key-123"

# cvss-fetcher 로그 확인
docker logs pwnable_3rd-cvss-fetcher-1 --tail 50
```

**예상 로그 패턴:**
- ✅ `"Attempting NVD API request for CVE-XXXX-XXXX"`
- ✅ `"Successfully fetched CVSS from NVD: CVE-XXXX-XXXX = X.X (version 3.1)"`
- NVD 실패 시:
  - ✅ `"NVD fetch failed for CVE-XXXX-XXXX, falling back to Perplexity"`
  - ✅ `"Perplexity로 CVSS 점수 조회 중"`

### 테스트: 데이터베이스에서 CVSS 소스 확인

```bash
# CVSS scores 테이블 확인
docker exec npm-threat-postgres psql -U postgres -d npm_threat_db \
  -c "SELECT cve_id, score, vector_string, source FROM cvss_scores ORDER BY created_at DESC LIMIT 10;"
```

**예상 결과:**
- 대부분의 항목이 `source = 'NVD'`
- Vector 문자열이 `CVSS:3.1/` 또는 `CVSS:3.0/`로 시작
- 폴백 항목은 `source = 'Perplexity'`일 수 있음

---

## ✅ 검증 체크리스트

### 보안 (Security)
- [ ] X-API-Key 없는 API 요청 거부됨 (401/403)
- [ ] 유효한 X-API-Key로 API 요청 수락됨 (200)
- [ ] 프론트엔드가 브라우저에 하드코딩된 API 키를 노출하지 않음

### 데이터 품질 (Data Quality)
- [ ] Stats 엔드포인트가 일관되게 UPPERCASE 키 반환
- [ ] CVSS 점수가 주로 NVD에서 가져옴 (로그/데이터베이스 확인)
- [ ] Perplexity는 NVD 실패 시에만 폴백으로 사용됨

### 신뢰성 (Reliability)
- [ ] Worker가 실패한 작업을 DLQ에 푸시함
- [ ] Worker가 Redis 연결 실패에서 살아남음
- [ ] Worker가 작업 실패 후에도 계속 처리함
- [ ] DLQ에 오류 메타데이터 포함됨 (error_msg, error_timestamp)

### 사용자 경험 (User Experience)
- [ ] 대시보드가 콘솔 오류 없이 로드됨
- [ ] 검색 기능이 엔드투엔드로 작동함
- [ ] Stats 카드가 숫자 값 표시 ("undefined" 아님)
- [ ] 보고서 생성이 합리적인 시간(~2분) 내에 완료됨

---

## 🐛 문제 해결 (Troubleshooting)

### "모든 테스트가 연결 오류로 실패"
- 모든 Docker 컨테이너가 실행 중인지 확인: `docker-compose ps`
- Redis 확인: `docker exec npm-threat-redis redis-cli PING`
- Query API 확인: `curl http://localhost:8004/health`

### "Stats 테스트가 KeyError로 실패"
- query-api 재시작: `docker-compose restart query-api`
- 로그 확인: `docker logs pwnable_3rd-query-api-1 --tail 50`

### "DLQ 테스트가 빈 큐 표시"
- DLQ 메시지에 대한 Worker 로그 확인: `docker logs npm-threat-agent-orchestrator | grep DLQ`
- Redis 연결 확인: `docker exec npm-threat-redis redis-cli KEYS "*"`

### "프론트엔드에 API 키 오류 표시"
- `.env` 파일에 `VITE_QUERY_API_KEY=dev-api-key-123`이 있는지 확인
- 프론트엔드 재시작: `docker-compose restart web-frontend`
- 브라우저 캐시 지우고 다시 로드

---

## 📝 참고사항 (Notes)

- 자동화된 테스트는 빠르며 모든 배포 전에 실행해야 합니다.
- 수동 검증은 엔드투엔드 신뢰도를 제공하지만 더 오래 걸립니다.
- DLQ 테스트는 시간 경과에 따른 동작 관찰이 필요합니다. 각 배포 후 DLQ를 확인하세요.
- "NVD fetch failed" 메시지에 대한 로그를 모니터링하여 폴백 빈도를 추적하세요.

## 5. 다중 생태계 지원 검증 (Multi-Ecosystem Support Verification)

새롭게 추가된 npm, pip, apt 생태계 지원 기능을 검증합니다.

### 5.1 UI 확인 (UI Check)
1. 대시보드 페이지에 접속합니다.
2. 검색창 왼쪽에 **생태계 선택 드롭다운(npm, pip, apt)**이 표시되는지 확인합니다.
3. 기본값이 **NPM**인지 확인합니다.

### 5.2 PIP 패키지 검색 테스트 (PIP Package Search Test)
1. 드롭다운에서 **PIP**를 선택합니다.
2. 검색창에 `flask` 또는 `django`를 입력하고 검색합니다.
3. **결과 확인**:
   - 분석이 시작되고 "Analysis in progress" 메시지가 표시되는지 확인합니다.
   - 잠시 후 보고서가 생성되면, 해당 패키지의 Python 관련 CVE들이 조회되는지 확인합니다.
   - (선택 사항) `docker logs npm-threat-worker` 명령어로 로그를 확인하여 `ecosystem='pip'`가 전달되었는지 확인합니다.

### 5.3 CVE ID 검색 테스트 (CVE ID Search Test)
1. 생태계 선택과 관계없이 검색창에 `CVE-2022-31691` (또는 유효한 CVE ID)를 입력합니다.
2. **결과 확인**:
   - 패키지 검색이 아닌 **CVE 단독 보고서**가 생성되는지 확인합니다.
