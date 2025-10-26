# 팀원 개발 환경 세팅 가이드

## 🚀 빠른 시작 (5분)

### 1. 저장소 클론
```
git clone https://github.com/[your-username]/npm-threat-evaluator.git
cd npm-threat-evaluator
```

### 2. 환경 변수 설정
```
cp .env.example .env
```

`.env` 파일을 열어서 다음 항목만 수정:
- `NT_PERPLEXITY_API_KEY`: 본인의 Perplexity API 키
- `NT_CLAUDE_API_KEY`: 본인의 Claude API 키
- `NT_GPT5_API_KEY`: 본인의 GPT-5 API 키

### 3. Docker 실행
```
docker-compose up -d
```

### 4. 확인
- API 테스트: http://localhost:8004/api/v1/query?package=lodash
- 웹 대시보드: http://localhost:5173

끝! 🎉

## 📝 개발 워크플로우

### 코드 수정 후 확인
1. 파일 저장
2. 자동으로 서비스 재시작 (기다리기만 하면 됨)
3. 브라우저 새로고침

### 로그 확인
```
# 전체 로그
docker-compose logs -f

# 특정 서비스
docker-compose logs -f threat-agent
```

### DB 확인
```
docker-compose exec postgres psql -U ntuser -d threatdb

# 테이블 목록
\dt

# 쿼리 예시
SELECT * FROM package_cve_mapping LIMIT 5;
```

### 서비스 재시작
```
# 특정 서비스만
docker-compose restart analyzer

# 전체 재시작
docker-compose restart
```

## 🛠️ 개발 환경 구조

### 포트 매핑
- 8000: MappingCollector
- 8001: EPSSFetcher
- 8002: ThreatAgent
- 8003: Analyzer
- 8004: QueryAPI
- 5173: WebFrontend
- 5432: PostgreSQL
- 6379: Redis

### 헬스체크
각 서비스가 정상 동작하는지 확인:
```
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
```

## ⚠️ 주의사항

1. **`.env` 파일은 절대 커밋하지 마세요!**
   - API 키가 노출되면 보안 문제가 발생합니다
   - `.gitignore`에 이미 등록되어 있으니 확인하세요

2. **포트 충돌 시 해결방법:**
   ```
   docker-compose down
   # Linux/Mac
   lsof -ti:8000 | xargs kill -9
   # Windows
   netstat -ano | findstr :8000
   taskkill /PID [프로세스ID] /F
   ```

3. **데이터 완전 초기화 (주의!):**
   ```
   docker-compose down -v
   docker-compose up -d
   ```
   ⚠️ 이 명령은 모든 데이터베이스 데이터를 삭제합니다!

4. **빌드 캐시 문제:**
   ```
   docker-compose build --no-cache
   docker-compose up -d
   ```

## 🔧 트러블슈팅

### 문제: Postgres가 Ready 상태가 안 됨
```
docker-compose logs postgres
# 초기화 스크립트 오류 확인 후
docker-compose down -v
docker-compose up -d postgres
```

### 문제: Python 모듈을 찾을 수 없음
```
# 볼륨 마운트 확인
docker-compose config
# common_lib 경로가 올바른지 확인
```

### 문제: 프론트엔드가 API를 찾지 못함
1. QueryAPI가 실행 중인지 확인: `docker-compose ps`
2. 네트워크 연결 확인: `docker-compose exec web-frontend ping query-api`
3. 환경변수 확인: `docker-compose exec web-frontend env | grep VITE`

## 🆘 도움말

- Slack #dev-threats 채널에 질문하기
- [상세 문서](README.md) 참고
- [API 스펙](docs/API.md) 참고
- [아키텍처 설명](docs/ARCHITECTURE.md) 참고

## 📚 추가 학습 자료

- Docker Compose 공식 문서: https://docs.docker.com/compose/
- FastAPI 공식 문서: https://fastapi.tiangolo.com/
- React + Vite 가이드: https://vitejs.dev/guide/
