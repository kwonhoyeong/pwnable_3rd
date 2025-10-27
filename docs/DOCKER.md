# Docker 협업 개발 환경 가이드 (Docker Collaborative Development Guide)

## 아키텍처 개요 다이어그램(Architecture overview)
```
                ┌────────────────────┐
                │      Web SPA       │
                │  web-frontend:5173 │
                └─────────┬──────────┘
                          │
                          ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│MappingCollector│ │  CVSSFetcher  │ │ EPSSFetcher   │
│    8000       │ │    8006       │ │    8001       │
└──────┬────────┘ └──────┬────────┘ └──────┬────────┘
       │                 │                 │
       ▼                 ▼                 ▼
               ┌────────────────────┐
               │   ThreatAgent      │
               │       8002         │
               └────────┬───────────┘
                        ▼
               ┌────────────────────┐
               │     Analyzer       │
               │       8003         │
               └────────┬───────────┘
                        ▼
               ┌────────────────────┐
               │     QueryAPI       │
               │       8004         │
               └────────┬───────────┘
                        ▼
           ┌────────────────────────────┐
           │   SQLite (./data/)         │
           │   In-Memory Cache          │
           └────────────────────────────┘
```

모든 서비스는 `nt-network` 브리지 네트워크에서 통신하며, SQLite 파일 기반 데이터베이스와 인메모리 캐시를 공유합니다.

## 서비스별 환경변수(Environment variables per service)
| 서비스(Service) | 필수 환경변수(Required) | 설명(Description) |
|-----------------|------------------------|-------------------|
| 모든 Python 서비스 | `NT_DATABASE_URL`, `NT_CACHE_TTL`, `NT_LOG_LEVEL` | SQLite 데이터베이스 URL, 캐시 TTL(초), 로그 레벨 설정 |
| ThreatAgent, Analyzer | `NT_PERPLEXITY_API_KEY`, `NT_CLAUDE_API_KEY`, `NT_GPT5_API_KEY` | 외부 AI API 키 입력 |
| Web Frontend | `VITE_QUERY_API_BASE_URL` | 백엔드 QueryAPI 접속 URL |

> 참고: 환경변수는 `docker-compose.yml`에 기본값이 설정되어 있어 별도 `.env` 파일 없이도 실행 가능합니다.

## 볼륨 구조 및 데이터 영속성(Volume structure & data persistence)
- `./data`: SQLite 데이터베이스 파일(`threatdb.sqlite`)이 호스트의 `./data` 디렉터리에 저장되어 Git 저장소에 포함 가능합니다.
  - 각 서비스 컨테이너에서 `/app/data`로 바인드 마운트되어 공유됩니다.
  - 데이터베이스 초기화는 `scripts/init_db.py` 스크립트로 수행합니다.
- 애플리케이션 소스코드: 각 서비스 디렉터리가 `/app` 하위로 바인드 마운트되어 핫 리로드를 지원합니다.
  - `./common_lib:/app/common_lib` - 공통 라이브러리
  - `./<service>:/app/<service>` - 각 서비스별 소스코드
- 인메모리 캐시: cachetools 라이브러리를 사용한 TTL 캐시로 프로세스 재시작 시 초기화됩니다.

## 성능 최적화 팁(Performance optimization tips)
1. **의존성 캐시(Dependency cache)**: Python/Node 이미지는 requirements 및 package manifest만 먼저 복사하여 빌드 캐시 활용.
2. **리소스 제한(Resource limits)**: 팀 정책에 따라 `deploy.resources.limits`를 설정하면 로컬 개발 중 과도한 자원 사용을 방지할 수 있습니다.
3. **선택적 서비스 실행(Selective startup)**: 특정 기능만 개발할 때는 `docker-compose up analyzer query-api`처럼 필요한 컨테이너만 올려 빌드 시간을 단축합니다.
4. **로그 레벨(Log level)**: `.env`에서 `NT_LOG_LEVEL=WARNING`으로 조정하면 불필요한 로그 출력 감소.

## CI/CD 연계 전략(CI/CD integration)
- **검증 단계(Validation stage)**: CI 파이프라인에서 `docker-compose -f docker-compose.yml -f docker-compose.ci.yml up --build` 구조를 사용하면 테스트/린트용 설정을 별도로 관리할 수 있습니다.
- **데이터베이스 초기화(Database initialization)**:
  - `database/init-db.sqlite.sql`은 스키마 정의용 초기화 스크립트입니다.
  - `scripts/init_db.py`를 실행하여 데이터베이스를 초기화합니다: `python scripts/init_db.py`
  - 프로덕션 배포 시에는 별도 마이그레이션 도구(예: Alembic)를 추천합니다.
- **비밀 관리(Secrets management)**: CI에서는 환경변수 대신 GitHub Actions secrets 또는 HashiCorp Vault 같은 관리 도구와 연동해 API 키를 주입하세요.
- **아티팩트 빌드(Build artifacts)**: 프런트엔드/백엔드 배포용 이미지는 현재 개발용 Dockerfile을 기반으로 `COPY` 지시자를 추가해 프로덕션 전용 Dockerfile을 별도로 유지합니다.

## 문제 해결(Troubleshooting)
- **데이터베이스 초기화 실패**: `./data` 디렉터리가 없거나 권한 문제가 있을 경우, `mkdir -p ./data && python scripts/init_db.py`로 수동 초기화합니다.
- **SQLite 파일 접근 오류**: 컨테이너에서 SQLite 파일 접근 권한 문제 발생 시, `chmod 666 ./data/threatdb.sqlite`로 권한을 조정합니다.
- **Python 서비스가 모듈을 찾지 못할 때**: 볼륨 경로가 올바른지(`./common_lib:/app/common_lib`) 점검하십시오.
- **캐시가 작동하지 않을 때**: 인메모리 캐시는 프로세스 재시작 시 초기화되므로, 컨테이너 재시작 후 캐시 데이터가 사라지는 것은 정상입니다.
- **서비스 간 통신 실패**: 모든 서비스가 `nt-network`에 연결되어 있는지 `docker network inspect nt-network`로 확인합니다.
