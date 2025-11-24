# 백엔드 및 프론트엔드 검토 보고서

## 1. 백엔드 검토

### 1.1 QueryAPI (`query_api/app`)
- **✅ 인증 및 Rate Limiting 완료** (`main.py:18-172`): API 키 인증(`X-API-Key` 헤더) 및 `slowapi` 기반 속도 제한 구현 완료.
- **✅ 프로덕션 디버그 로깅 제거** (`main.py:72,102,124`): 환경 변수 기반 로그 제어로 개선.
- **Repository Layer** (`repository.py:20-185`):
  - SQL 파라미터 바인딩으로 `package`/`cve_id` 보호
  - **✅ `risk_score` 스키마 통일 완료**: DB에서 `risk_score`를 직접 조회하도록 수정
  - 페이지네이션 메타데이터는 `total_returned`만 제공 (전체 count는 미제공)
- **Service Layer** (`service.py:16-122`):
  - package와 cve_id 동시 제공 시 `ValueError` 발생 (현재 동작 유지)
  - **✅ AI 가중 `risk_score` 사용**: DB의 `risk_score`를 기반으로 `risk_label` 파생
  - 캐시 무효화: TTL 만료 시까지 데이터 유지 (수동 무효화 없음)

### 1.2 ThreatAgent (`threat_agent/app/services.py`)
- **언어 프롬프팅**: Sanitization으로 한국어 요약 보장, 문서의 "한국어/영어" 주장은 실제로 다국어 명시 안 됨
- **심각도 추출**: `_extract_severity`로 파생된 심각도는 저장되지 않음 (컨텍스트 손실)
- **✅ 오류 처리 개선**: Perplexity/Claude 예외에 대한 graceful degradation 구현 (fallback 메시지 반환)

### 1.3 공통 이슈
- **환경변수 보안**: `.env` 파일의 실제 API 키는 반드시 gitignore 처리 필요
- **Docker Compose**: `agent-orchestrator` 빌드 컨텍스트가 `analyzer/Dockerfile`을 참조하나 오케스트레이터 런타임과 맞지 않을 수 있음

### 1.4 권장사항
1. ~~QueryAPI에 인증/권한 미들웨어 도입~~ ✅ 완료
2. ~~백엔드 응답 모델을 프론트엔드 기대와 일치시키기 (`risk_score` vs `priority_score`)~~ ✅ 완료
3. ~~AI 파생 `risk_score`를 영구 저장하고 API로 노출~~ ✅ 완료
4. ~~외부 AI 호출에 재시도/백오프 추가 및 구조화된 오류 봉투 제공~~ ✅ 완료
5. Docker 설정 강화 (non-root 사용자, 헬스 엔드포인트)

## 2. 프론트엔드 검토

### 2.1 API Layer (`web_frontend/src/api/endpoints.ts`)
- **✅ 스키마 통일 완료**: `CVEDetail.risk_score` 및 `HistoryRecord.risk_score`로 통일
- `HistoryResponse`는 `total_returned` 사용 (일관성 유지)

### 2.2 Dashboard Components
- `RecentScansTable.tsx:52-86`: `risk_score.toFixed(1)` 안전 가드 적용
- **✅ DashboardPage.tsx 수정 완료**: 사용자가 입력한 `version` 파라미터를 API에 전달하도록 수정
- **✅ 에러 배너 개선**: `getErrorMessage` 유틸리티를 활용하여 백엔드 오류 상세 표시

### 2.3 Build/Dev Config
- `vite.config.ts`는 `/api`를 `localhost:8004`로 프록시 (프로덕션 경로는 문서화 필요)
- Vite `.env` 설정: `VITE_QUERY_API_BASE_URL` 환경변수 사용 가능

### 2.4 권장사항
1. ~~API 컨버터를 업데이트하여 `risk_score` (AI 가중치) vs `priority_score` 구분~~ ✅ 완료
2. ~~사용자가 제공한 `version`을 백엔드 쿼리에 전달~~ ✅ 완료
3. ~~UI에서 백엔드 오류를 toast/배너로 표시~~ ✅ 완료
4. Vite 환경 변수 및 프록시 기대사항 문서화

## 3. 문서 업데이트
- ~~README에 새로운 검토 하이라이트, 현재 백엔드 인증 격차, 프론트엔드/API 스키마 정렬 작업 포함~~ ✅ 완료
- `.env` 변경 후 Docker 서비스 재시작을 위한 운영 가이드 추가 권장

## 4. 최근 개선사항 (2025-11-23)

### 완료된 작업
1. **✅ API Key 인증**: `X-API-Key` 헤더 기반 인증 시스템 구현
2. **✅ Rate Limiting**: slowapi를 통한 엔드포인트별 요청 제한
3. **✅ 데이터 스키마 통일**: `priority_score` → `risk_score`로 전면 변경
4. **✅ DB 통합**: `analysis_results` 테이블의 `risk_score`를 직접 사용
5. **✅ 안정성 강화**: AI 호출 실패 시 graceful degradation
6. **✅ 프론트엔드 버전 파라미터**: 사용자 입력 버전이 API에 전달됨
7. **✅ 오류 메시지 개선**: 구조화된 에러 응답을 UI에 표시
8. **✅ 문서 현행화**: API.md, README.md, docker-compose.yml 업데이트

### 검증 결과
- `scripts/verify_system.py`를 통한 시스템 검증 완료
- 모든 인증, 스키마, Rate Limiting 테스트 통과
