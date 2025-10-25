# MappingCollector 모듈 가이드 (MappingCollector Module Guide)

## 개요(Overview)
- 역할(Role): npm 패키지명과 버전 범위를 바탕으로 영향받는 CVE 목록을 주기적으로 수집합니다.
- 실행 형태(Runtime): FastAPI 백그라운드 서비스 + 비주기성 작업을 위한 `MappingScheduler`.
- 주요 의존성(Core deps): Python 3.11, FastAPI, SQLAlchemy, PostgreSQL, Redis(optional cache hook).

## 사전 준비(Prerequisites)
1. PostgreSQL 데이터베이스와 연결 문자열(예: `postgresql+asyncpg://user:pass@localhost:5432/mapping`).
2. (선택) Redis 인스턴스.
3. 환경 변수 `.env` (예시):
   ```env
   DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/mapping
   REDIS_URL=redis://localhost:6379/0
   ```

## 설치 및 실행(Setup & Run)
```bash
pip install -r requirements.txt  # 또는 poetry install
python -m uvicorn mapping_collector.app.main:app --reload
```
- 서비스 기동 후 헬스 체크: `curl http://127.0.0.1:8000/health`

## 스케줄러 테스트(Testing the scheduler loop)
- 단일 주기 테스트(Single cycle test):
  ```bash
  python - <<'PY'
  import asyncio
  from mapping_collector.app.scheduler import MappingScheduler

  async def main() -> None:
      scheduler = MappingScheduler(interval_seconds=0)
      await scheduler._run_once()  # 데모용 내부 호출(demo-only private invocation)

  asyncio.run(main())
  PY
  ```
- 위 스크립트 실행 시 더미 패키지 큐를 읽고 저장 레이어가 호출되는지 로그로 확인합니다.

## API 인터페이스(API Interface)
- `/health` (GET): 서비스 상태 확인.
- 향후 확장 포인트(Future hooks): Kafka/Redis Stream 이벤트 수신 → `MappingRepository.enqueue_package` 에 투입.

## 데이터베이스 스키마(Database Schema)
- `db/schema.sql` 참고.
- 핵심 테이블(Table): `package_cve_mapping(package, version_range, cve_ids, collected_at)`.

## 로깅/예외(Log & Exception)
- `common_lib.logger.get_logger` 를 통해 구조화 로그 생성.
- 모든 외부 호출은 `MappingService.fetch_cves` 내부에서 재시도 로직 추가 예정.

## Docker 실행(Docker Run)
```bash
docker build -t mapping-collector .
docker run --rm -p 8000:8000 --env-file ../.env mapping-collector
```

## 샘플 입력/출력(Sample IO)
- 입력(Input JSON):
  ```json
  {
    "package": "lodash",
    "version_range": "<4.17.21",
    "collected_at": "2025-10-24T12:34:56Z"
  }
  ```
- 출력(Output JSON):
  ```json
  {
    "package": "lodash",
    "version_range": "<4.17.21",
    "cve_ids": ["CVE-2023-1234", "CVE-2022-5678"],
    "collected_at": "2025-10-24T12:34:56Z"
  }
  ```
