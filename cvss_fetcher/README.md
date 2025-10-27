# CVSSFetcher 모듈(CVSSFetcher Module)

CVSSFetcher는 CVE 식별자를 입력받아 CVSS(Base Score) 정보를 수집하고 PostgreSQL에 저장하는 비동기 FastAPI 서비스입니다.

## 주요 기능(Key Features)
- CVE ID 입력 시 NVD API에서 CVSS v3 점수 조회
- 오류 발생 시 재시도 및 로깅 처리
- PostgreSQL에 점수와 벡터 저장(Upsert)
- 독립 실행 가능한 FastAPI 마이크로서비스

## 실행 방법(How to Run)
```bash
# 루트에서 가상환경 생성 및 의존성 설치(Create venv & install deps from repo root)
cd ..
python3 -m venv .venv && source .venv/bin/activate
python3 -m pip install -r requirements.txt

# 루트 .env 파일 구성(Set environment via .env)
cp .env.example .env  # 필요한 경우 API 키/DSN 수정

# 애플리케이션 실행(Run FastAPI service)
python3 -m uvicorn cvss_fetcher.app.main:app --reload --port 8005
```

## 테스트 입력 예제(Sample Input)
```json
{
  "cve_id": "CVE-2023-1234"
}
```

## 데이터베이스 스키마(Database Schema)
- `db/schema.sql` 파일 참조

## Docker 실행(Docker Run)
```bash
docker build -t cvss-fetcher:dev -f cvss_fetcher/Dockerfile .
docker run --rm -p 8005:8005 cvss-fetcher:dev
```
