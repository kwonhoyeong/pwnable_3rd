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
│MappingCollector│ │ EPSSFetcher   │ │ ThreatAgent   │
│    8000       │ │    8001       │ │    8002       │
└──────┬────────┘ └──────┬────────┘ └──────┬────────┘
       │                 │                 │
       ▼                 ▼                 ▼
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
           │ PostgreSQL (nt-postgres)   │
           │ Redis (nt-redis)           │
           └────────────────────────────┘
```

모든 서비스는 `nt-network` 브리지 네트워크에서 통신하며, PostgreSQL과 Redis는 공통 상태 저장소로 활용됩니다.

## 서비스별 환경변수(Environment variables per service)
| 서비스(Service) | 필수 환경변수(Required) | 설명(Description) |
|-----------------|------------------------|-------------------|
| 모든 Python 서비스 | `NT_POSTGRES_DSN`, `NT_REDIS_URL`, `NT_LOG_LEVEL` | 데이터베이스/캐시 DSN 및 로그 레벨 설정 |
| ThreatAgent | `NT_PERPLEXITY_API_KEY`, `NT_CLAUDE_API_KEY`, `NT_GPT5_API_KEY` | 외부 AI API 키 입력 |
| Web Frontend | `VITE_QUERY_API_URL` | 백엔드 QueryAPI 접속 URL |
| Postgres | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | 기본 데이터베이스 자격 증명 |

> 참고: `.env.example`을 복사해 `.env`로 사용하면 Docker Compose가 자동으로 읽어들입니다.

## 볼륨 구조 및 데이터 영속성(Volume structure & data persistence)
- `postgres_data`: `/var/lib/postgresql/data`에 마운트되어 DB 데이터를 영구 저장합니다.
- `redis_data`: `/data`에 마운트되어 Redis 스냅샷을 유지합니다.
- 애플리케이션 소스코드: 각 서비스 디렉터리가 `/app` 하위로 바인드 마운트되어 핫 리로드를 지원합니다.

## 성능 최적화 팁(Performance optimization tips)
1. **의존성 캐시(Dependency cache)**: Python/Node 이미지는 requirements 및 package manifest만 먼저 복사하여 빌드 캐시 활용.
2. **리소스 제한(Resource limits)**: 팀 정책에 따라 `deploy.resources.limits`를 설정하면 로컬 개발 중 과도한 자원 사용을 방지할 수 있습니다.
3. **선택적 서비스 실행(Selective startup)**: 특정 기능만 개발할 때는 `docker-compose up analyzer query-api`처럼 필요한 컨테이너만 올려 빌드 시간을 단축합니다.
4. **로그 레벨(Log level)**: `.env`에서 `NT_LOG_LEVEL=WARNING`으로 조정하면 불필요한 로그 출력 감소.

## CI/CD 연계 전략(CI/CD integration)
- **검증 단계(Validation stage)**: CI 파이프라인에서 `docker-compose -f docker-compose.yml -f docker-compose.ci.yml up --build` 구조를 사용하면 테스트/린트용 설정을 별도로 관리할 수 있습니다.
- **마이그레이션(Migration)**: `init-db.sql`은 개발 편의를 위한 초기 데이터이므로, 프로덕션 배포 시에는 별도 마이그레이션 도구(예: Alembic)를 추천합니다.
- **비밀 관리(Secrets management)**: CI에서는 `.env` 대신 GitHub Actions secrets 또는 HashiCorp Vault 같은 관리 도구와 연동해 환경변수를 주입하세요.
- **아티팩트 빌드(Build artifacts)**: 프런트엔드/백엔드 배포용 이미지는 현재 개발용 Dockerfile을 기반으로 `COPY` 지시자를 추가해 프로덕션 전용 Dockerfile을 별도로 유지합니다.

## 문제 해결(Troubleshooting)
- Postgres 컨테이너가 Ready 상태가 아니라면 `docker-compose logs postgres`로 초기화 로그를 확인하고, 필요 시 `docker-compose down -v`로 볼륨을 재생성합니다.
- Redis 핫 로드는 저장소 바인드 마운트로 즉시 반영되지만, 간혹 모듈 해제 문제가 있을 경우 `docker-compose restart redis`로 재시작합니다.
- Python 서비스가 모듈을 찾지 못할 때는 볼륨 경로가 올바른지(`./common_lib:/app/common_lib`) 점검하십시오.
