# Docker 협업 개발 환경 가이드 (Docker Collaborative Development Guide)

**문서 버전**: 2.0  
**최종 업데이트**: 2025-12-01  
**대상 독자**: DevOps 엔지니어, 개발팀, 인프라 담당자

---

## 목차
1. [아키텍처 개요](#1-아키텍처-개요)
2. [로컬 개발 환경](#2-로컬-개발-환경)
3. [프로덕션 배포 고려사항](#3-프로덕션-배포-고려사항)
4. [모니터링 및 관찰성](#4-모니터링-및-관찰성)
5. [백업 및 복구](#5-백업-및-복구)
6. [성능 최적화](#6-성능-최적화)
7. [보안 강화](#7-보안-강화)
8. [문제 해결](#8-문제-해결)

---

## 1. 아키텍처 개요

### 1.1 시스템 다이어그램

```
                 ┌────────────────────┐
                 │   Web Frontend     │
                 │  (React + Vite)    │
                 │  Port: 5173        │
                 └─────────┬──────────┘
                           │ HTTP
                           ▼
┌──────────────────────────────────────────────────────────┐
│                   API Gateway Layer                       │
│                                                          │
│  ┌──────────────┐   ┌──────────────┐   ┌─────────────┐ │
│  │MappingCollector│  │  CVSSFetcher │   │ EPSSFetcher │ │
│  │    8000       │  │    8006      │   │    8001     │ │
│  └──────┬────────┘  └──────┬───────┘   └──────┬──────┘ │
│         │                  │                   │        │
│         ▼                  ▼                   ▼        │
│  ┌──────────────┐   ┌──────────────┐                   │
│  │ ThreatAgent  │   │   Analyzer   │                   │
│  │    8002      │   │     8003     │                   │
│  └──────┬────────┘  └──────┬───────┘                   │
│         │                  │                            │
│         └──────┬───────────┘                            │
│                ▼                                        │
│         ┌─────────────┐                                │
│         │  QueryAPI   │                                │
│         │    8004     │                                │
│         └──────┬──────┘                                │
└────────────────┼──────────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
    ▼                         ▼
┌─────────┐            ┌──────────────┐
│  Redis  │            │  PostgreSQL  │
│  6379   │            │     5432     │
│         │            │              │
│ • Cache │            │ • CVE Data   │
│ • Queue │            │ • Scores     │
│ • Locks │            │ • Analysis   │
└─────────┘            └──────────────┘
```

### 1.2 서비스별 역할 및 기술 스택

| 서비스 | 역할 | 기술 스택 | 리소스 요구사항 |
|--------|------|----------|----------------|
| **MappingCollector** | CVE 수집 | FastAPI, Perplexity | CPU: 0.5, Mem: 512MB |
| **CVSSFetcher** | CVSS 점수 | FastAPI, NVD API | CPU: 0.3, Mem: 256MB |
| **EPSSFetcher** | EPSS 확률 | FastAPI, FIRST.org | CPU: 0.3, Mem: 256MB |
| **ThreatAgent** | 위협 분석 | FastAPI, Claude | CPU: 1.0, Mem: 1GB |
| **Analyzer** | 최종 분석 | FastAPI, GPT-5 | CPU: 1.0, Mem: 1GB |
| **QueryAPI** | 외부 API | FastAPI, slowapi | CPU: 0.5, Mem: 512MB |
| **Frontend** | UI | React 18, Vite | CPU: 0.3, Mem: 256MB |
| **Redis** | 캐시/큐 | Redis 7 | CPU: 0.5, Mem: 512MB |
| **PostgreSQL** | DB | PostgreSQL 15 | CPU: 1.0, Mem: 1GB |

**총 리소스 (최소):**
- CPU: 5.4 cores
- Memory: 5.3GB
- Disk: 10GB (DB + 로그)

### 1.3 네트워크 토폴로지

**개발 환경 (docker-compose):**
```
┌─────────────────────────────────────┐
│        nt-network (Bridge)          │
│                                     │
│  서비스 간 통신: service_name:port  │
│  예: http://query-api:8004         │
└─────────────────────────────────────┘
        │
        └──► Host: localhost:{port}
```

**프로덕션 환경 (Kubernetes - 미래):**
```
┌─────────────────────────────────────┐
│       Service Mesh (Istio)          │
│                                     │
│  mTLS, Circuit Breaking, Telemetry  │
└─────────────────────────────────────┘
```

---

## 2. 로컬 개발 환경

### 2.1 환경 변수 구성

**필수 환경 변수 체크리스트:**

```bash
# .env 파일 템플릿
cp .env.example .env

# 필수 변수 설정
NT_DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/npm_threat_db
NT_REDIS_URL=redis://redis:6379/0

# AI API 키 (선택)
NT_PERPLEXITY_API_KEY=your_key_here
NT_CLAUDE_API_KEY=your_key_here
NT_GPT5_API_KEY=your_key_here
NVD_API_KEY=your_key_here

# QueryAPI 인증
NT_QUERY_API_KEYS=dev-key-123,team-key-456

# 프론트엔드
VITE_API_URL=http://localhost:8004
VITE_QUERY_API_KEY=dev-key-123
```

**환경 변수 우선순위:**
1. `.env` 파일
2. `docker-compose.yml`의 `environment`
3. Shell 환경 변수

### 2.2 빠른 시작 가이드

```bash
# 1. 의존성 확인
docker --version  # 20.10+
docker-compose --version  # 1.29+

# 2. 이미지 빌드 (첫 실행)
docker-compose build

# 3. 서비스 시작
docker-compose up -d

# 4. 로그 확인
docker-compose logs -f query-api

# 5. 헬스 체크
curl http://localhost:8004/health
```

**예상 시작 시간:**
- 첫 빌드: 5-10분 (의존성 다운로드)
- 재시작: 30초 (이미지 캐시 활용)

### 2.3 볼륨 구조 상세

```
프로젝트 루트/
├── data/                    # PostgreSQL 데이터 (영구)
│   └── threatdb.sqlite     # SQLite (개발용)
│
├── logs/                    # 애플리케이션 로그 (선택)
│   ├── query-api.log
│   ├── worker.log
│   └── analyzer.log
│
├── common_lib/              # 공통 라이브러리 (바인드 마운트)
│   └── ...                 # 코드 변경 시 자동 반영
│
└── {service}/               # 각 서비스 (바인드 마운트)
    └── app/
```

**바인드 마운트 vs 볼륨:**

| 유형 | 사용처 | 장점 | 단점 |
|------|--------|------|------|
| **Bind Mount** | 소스 코드 | 핫 리로드, IDE 동기화 | 성능 오버헤드 (macOS) |
| **Named Volume** | DB 데이터 | 빠름, 백업 용이 | 호스트에서 직접 접근 어려움 |

**최적 구성:**
```yaml
services:
  query-api:
    volumes:
      - ./query_api:/app/query_api:cached  # 소스 (Bind)
      - ./common_lib:/app/common_lib:cached  # 공통 (Bind)
  
  postgres:
    volumes:
      - postgres_data:/var/lib/postgresql/data  # DB (Volume)

volumes:
  postgres_data:
```

### 2.4 개발 워크플로우

**코드 변경 → 반영 과정:**

```bash
# Python 코드 변경 (query_api/app/service.py)
vim query_api/app/service.py

# 자동 리로드 (uvicorn --reload)
# → 변경 감지 → 서비스 재시작 (1-2초)

# 확인
curl http://localhost:8004/api/v1/stats
```

**의존성 추가:**

```bash
# 1. requirements.txt 수정
echo "numpy==1.24.0" >> requirements.txt

# 2. 이미지 재빌드
docker-compose build query-api

# 3. 서비스 재시작
docker-compose up -d query-api
```

---

## 3. 프로덕션 배포 고려사항

### 3.1 Docker vs Kubernetes

**현재 상황 (Docker Compose):**
- ✅ 장점: 간단, 빠른 개발
- ❌ 단점: 수평 확장 어려움, HA 미지원

**프로덕션 전환 (Kubernetes):**

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: query-api
spec:
  replicas: 3  # 수평 확장
  selector:
    matchLabels:
      app: query-api
  template:
    metadata:
      labels:
        app: query-api
    spec:
      containers:
      - name: query-api
        image: your-registry/query-api:v1.0
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        env:
        - name: NT_DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-credentials
              key: url
```

**마이그레이션 로드맵:**

| 단계 | 트래픽 | 추천 환경 |
|------|--------|----------|
| 1: MVP | < 10 RPS | Docker Compose |
| 2: Alpha | 10-50 RPS | Docker Compose + Load Balancer |
| 3: Beta | 50-200 RPS | Kubernetes (3 nodes) |
| 4: Production | 200+ RPS | Kubernetes (Auto-scaling) |

### 3.2 이미지 최적화

**현재 이미지 크기:**
```
REPOSITORY          TAG       SIZE
query-api          latest    1.2GB
analyzer           latest    1.5GB
frontend           latest    800MB
```

**최적화 전략:**

```dockerfile
# Before (1.2GB)
FROM python:3.11
COPY . /app
RUN pip install -r requirements.txt

# After (600MB - 50% 감소)
FROM python:3.11-slim as builder
WORKDIR /app
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . /app
ENV PATH=/root/.local/bin:$PATH
```

**Multi-Stage Build 장점:**
- 빌드 도구 제외 → 크기 감소
- 보안 취약점 감소
- 레이어 캐싱 최적화

### 3.3 보안 강화

**비밀 관리:**

```yaml
# docker-compose.prod.yml
services:
  query-api:
    environment:
      - NT_DATABASE_URL=${NT_DATABASE_URL}  # 환경 변수로 주입
    secrets:
      - api_keys
      - db_password

secrets:
  api_keys:
    external: true
  db_password:
    external: true
```

**외부 비밀 관리 도구:**
- AWS Secrets Manager
- HashiCorp Vault
- Azure Key Vault

**네트워크 격리:**

```yaml
networks:
  frontend:  # 외부 노출
  backend:   # 내부 전용
  database:  # DB만 접근

services:
  query-api:
    networks:
      - frontend
      - backend
  
  postgres:
    networks:
      - database  # 외부 접근 차단
```

### 3.4 리소스 제한

```yaml
services:
  query-api:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
```

**Limits vs Reservations:**
- **Limits**: 최대 사용 가능 (초과 시 OOM Kill)
- **Reservations**: 보장 리소스 (스케줄링 시 고려)

---

## 4. 모니터링 및 관찰성

### 4.1 로깅 전략

**로그 레벨별 용도:**

| 레벨 | 용도 | 예시 | 프로덕션 사용 |
|------|------|------|--------------|
| DEBUG | 개발 디버깅 | "Cache key: mapping:npm:lodash" | ❌ |
| INFO | 정상 동작 | "Job completed: lodash" | ✅ |
| WARNING | 주의 필요 | "NVD API timeout, using fallback" | ✅ |
| ERROR | 오류 발생 | "Database connection failed" | ✅ |
| CRITICAL | 시스템 중단 | "Redis completely unavailable" | ✅ |

**로그 집계 (ELK Stack):**

```yaml
# docker-compose.monitoring.yml
services:
  elasticsearch:
    image: elasticsearch:8.5
    environment:
      - discovery.type=single-node
  
  logstash:
    image: logstash:8.5
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
  
  kibana:
    image: kibana:8.5
    ports:
      - "5601:5601"
```

**Logstash 설정:**

```ruby
# logstash.conf
input {
  file {
    path => "/var/log/app/*.log"
    codec => json
  }
}

filter {
  # Request ID 추출
  grok {
    match => { "message" => "\[%{DATA:request_id}\]" }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "app-logs-%{+YYYY.MM.dd}"
  }
}
```

### 4.2 메트릭 수집 (Prometheus)

**Prometheus + Grafana 구성:**

```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

**애플리케이션 메트릭 노출:**

```python
# query_api/app/metrics.py
from prometheus_client import Counter, Histogram, generate_latest

request_count = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('api_request_duration_seconds', 'API request duration')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

**Grafana 대시보드 예시:**

```
┌───────────────────────────────────────────┐
│  npm-threat-db Dashboard                  │
├───────────────────────────────────────────┤
│  RPS: 250 req/s  │  Errors: 0.1%         │
│  P95 Latency: 120ms │  Cache Hit: 82%    │
├───────────────────────────────────────────┤
│  [그래프] Request Rate (last 24h)          │
│  [그래프] Error Rate                       │
│  [그래프] Database Connections             │
└───────────────────────────────────────────┘
```

### 4.3 헬스 체크 구현

**상세 헬스 체크:**

```python
# query_api/app/health.py
@app.get("/health")
async def health_check():
    checks = {
        "database": await check_database(),
        "redis": await check_redis(),
        "disk_space": check_disk_space(),
        "memory": check_memory()
    }
    
    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if all_healthy else "unhealthy",
            "checks": checks,
            "timestamp": datetime.now().isoformat()
        }
    )
```

**Kubernetes Probes:**

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8004
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8004
  initialDelaySeconds: 5
  periodSeconds: 5
```

### 4.4 알람 설정

**Prometheus AlertManager:**

```yaml
# alertmanager.yml
groups:
- name: api_alerts
  rules:
  - alert: HighErrorRate
    expr: rate(api_requests_total{status=~"5.."}[5m]) > 0.05
    for: 5m
    annotations:
      summary: "Error rate above 5%"
  
  - alert: HighLatency
    expr: histogram_quantile(0.95, api_request_duration_seconds) > 1.0
    for: 5m
    annotations:
      summary: "P95 latency above 1s"
```

---

## 5. 백업 및 복구

### 5.1 PostgreSQL 백업

**자동 백업 스크립트:**

```bash
#!/bin/bash
# scripts/backup_db.sh

BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"

# Dump
docker exec npm-threat-postgres pg_dump -U postgres npm_threat_db | gzip > $BACKUP_FILE

# 7일 이상 된 백업 삭제
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE"
```

**Cron 설정:**

```cron
# 매일 새벽 2시 백업
0 2 * * * /path/to/scripts/backup_db.sh
```

**복구 절차:**

```bash
# 1. 백업 파일 확인
ls -lh /backups/

# 2. 복구
gunzip < /backups/db_backup_20251201_020000.sql.gz | \
  docker exec -i npm-threat-postgres psql -U postgres -d npm_threat_db

# 3. 데이터 확인
docker exec npm-threat-postgres psql -U postgres -d npm_threat_db -c "SELECT COUNT(*) FROM analysis_results;"
```

### 5.2 Redis 백업

**RDB 스냅샷:**

```bash
# redis.conf
save 900 1    # 15분마다, 1개 이상 변경 시
save 300 10   # 5분마다, 10개 이상 변경 시
save 60 10000 # 1분마다, 10000개 이상 변경 시

# 즉시 저장
docker exec npm-threat-redis redis-cli BGSAVE
```

**AOF (Append-Only File):**

```bash
# redis.conf
appendonly yes
appendfsync everysec  # 매초 디스크 동기화
```

### 5.3 재해 복구 (DR) 시나리오

**시나리오 1: 데이터 손실**

```bash
# 1. 서비스 중지
docker-compose down

# 2. 백업에서 복구
./scripts/restore_db.sh /backups/latest.sql.gz

# 3. 서비스 재시작
docker-compose up -d

# 4. 검증
curl http://localhost:8004/api/v1/stats
```

**시나리오 2: 전체 시스템 장애**

```bash
# 1. 새 서버 준비
# 2. Docker 설치
# 3. 코드 배포
git clone https://github.com/your-org/project.git

# 4. 백업 복사
scp backup-server:/backups/*.gz ./backups/

# 5. 복구 및 시작
./scripts/restore_all.sh
docker-compose up -d
```

**RTO/RPO 목표:**
- **RTO** (Recovery Time Objective): 1시간
- **RPO** (Recovery Point Objective): 1일 (하루 백업)

---

## 6. 성능 최적화

### 6.1 Docker 빌드 최적화

**레이어 캐싱:**

```dockerfile
# Bad (매번 재빌드)
COPY . /app
RUN pip install -r requirements.txt

# Good (의존성 캐싱)
COPY requirements.txt /app/
RUN pip install -r requirements.txt
COPY . /app  # 코드만 변경 시 여기부터 재빌드
```

**BuildKit 사용:**

```bash
# 환경 변수 설정
export DOCKER_BUILDKIT=1

# 빌드 (30-50% 빠름)
docker-compose build
```

### 6.2 네트워크 최적화

**컨테이너 간 통신:**

```yaml
# 내부 통신 시 localhost 대신 서비스명 사용
services:
  query-api:
    environment:
      - REDIS_URL=redis://redis:6379  # ✅ Good
      # - REDIS_URL=redis://localhost:6379  # ❌ Bad
```

**네트워크 모드:**

```yaml
# Bridge (기본) - 격리
network_mode: bridge

# Host - 최고 성능, 격리 없음
network_mode: host
```

### 6.3 리소스 모니터링

**실시간 모니터링:**

```bash
# CPU/Memory 사용량
docker stats

# 특정 컨테이너
docker stats query-api analyzer
```

**Top 프로세스:**

```bash
# 컨테이너 내부 프로세스
docker exec query-api top
```

---

## 7. 보안 강화

### 7.1 취약점 스캔

**Trivy 사용:**

```bash
# 이미지 스캔
trivy image query-api:latest

# 결과 예시
Total: 15 (UNKNOWN: 0, LOW: 5, MEDIUM: 8, HIGH: 2, CRITICAL: 0)
```

**자동 스캔 (CI/CD):**

```yaml
# .github/workflows/security.yml
- name: Run Trivy
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: 'query-api:${{ github.sha }}'
    severity: 'CRITICAL,HIGH'
```

### 7.2 컨테이너 강화

**Read-Only Root Filesystem:**

```yaml
services:
  query-api:
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
```

**Non-Root User:**

```dockerfile
# Dockerfile
RUN adduser --disabled-password --gecos '' appuser
USER appuser
```

### 7.3 네트워크 보안

**방화벽 규칙:**

```bash
# iptables 예시
iptables -A INPUT -p tcp --dport 8004 -s 10.0.0.0/8 -j ACCEPT
iptables -A INPUT -p tcp --dport 8004 -j DROP
```

---

## 8. 문제 해결

### 8.1 일반적인 문제

#### 문제 1: "Cannot connect to the Docker daemon"

**증상:**
```
ERROR: Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**해결:**
```bash
# Docker 데몬 시작
sudo systemctl start docker

# 권한 확인
sudo usermod -aG docker $USER
newgrp docker
```

#### 문제 2: "Port already in use"

**증상:**
```
Error: Bind for 0.0.0.0:8004 failed: port is already allocated
```

**해결:**
```bash
# 포트 사용 프로세스 확인
lsof -i :8004

# 프로세스 종료
kill -9 <PID>

# 또는 다른 포트 사용
docker-compose up -d --scale query-api=1 -p 8005:8004
```

#### 문제 3: "Database connection refused"

**증상:**
```
psycopg2.OperationalError: could not connect to server: Connection refused
```

**해결:**
```bash
# PostgreSQL 컨테이너 확인
docker-compose ps postgres

# 로그 확인
docker-compose logs postgres

# 재시작
docker-compose restart postgres

# 연결 테스트
docker exec -it npm-threat-postgres psql -U postgres -d npm_threat_db
```

### 8.2 로그 분석

**에러 로그 검색:**

```bash
# 최근 100줄
docker-compose logs --tail=100 query-api

# 에러만 필터
docker-compose logs query-api | grep ERROR

# 실시간 추적
docker-compose logs -f query-api
```

### 8.3 성능 문제 디버깅

**느린 컨테이너 식별:**

```bash
# 1. 리소스 사용량 확인
docker stats --no-stream

# 2. 프로세스 확인
docker exec query-api ps aux

# 3. 네트워크 확인
docker exec query-api netstat -tulpn
```

**DB 쿼리 분석:**

```sql
-- 느린 쿼리 확인
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

### 8.4 재시작 체크리스트

```bash
# 1. 현재 상태 확인
docker-compose ps

# 2. 안전한 종료
docker-compose down

# 3. 볼륨 정리 (선택 - 주의!)
# docker volume prune

# 4. 이미지 재빌드
docker-compose build

# 5. 서비스 시작
docker-compose up -d

# 6. 헬스 체크
for port in 8000 8001 8002 8003 8004; do
  echo "Checking port $port..."
  curl -f http://localhost:$port/health || echo "FAILED"
done
```

---

## 부록 A: docker-compose.yml 전체 구성 예시

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: npm_threat_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init-db.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "15432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - nt-network

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    networks:
      - nt-network

  query-api:
    build:
      context: .
      dockerfile: query_api/Dockerfile
    environment:
      - NT_DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/npm_threat_db
      - NT_REDIS_URL=redis://redis:6379/0
      - NT_QUERY_API_KEYS=${NT_QUERY_API_KEYS}
    volumes:
      - ./query_api:/app/query_api:cached
      - ./common_lib:/app/common_lib:cached
    ports:
      - "8004:8004"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - nt-network

volumes:
  postgres_data:
  redis_data:

networks:
  nt-network:
    driver: bridge
```

---

## 부록 B: 추천 도구

| 카테고리 | 도구 | 용도 |
|---------|------|------|
| **이미지 스캔** | Trivy, Snyk | 취약점 검사 |
| **로그 관리** | ELK Stack, Loki | 로그 집계 |
| **모니터링** | Prometheus, Grafana | 메트릭 수집/시각화 |
| **트레이싱** | Jaeger, Zipkin | 분산 추적 |
| **시크릿** | Vault, AWS Secrets | 비밀 관리 |
| **CI/CD** | GitHub Actions, GitLab CI | 자동 배포 |

---

**문서 마지막 업데이트**: 2025-12-01  
**문서 버전**: 2.0  
**작성자**: DevOps Team  
**다음 리뷰 예정**: 2026-01-01
