# CommonLib 모듈 가이드 (CommonLib Module Guide)

## 개요(Overview)
- 역할(Role): 모든 서비스가 공유하는 설정, 로깅, 데이터베이스, 캐시, AI 클라이언트 유틸리티를 제공합니다.
- 구조(Structure):
  - `config.py`: 환경 변수 로딩 + pydantic 설정 모델.
  - `logger.py`: 구조화 로거 설정.
  - `db.py`: SQLAlchemy AsyncEngine/세션 헬퍼.
  - `cache.py`: Redis 클라이언트 헬퍼.
  - `ai_clients/`: `IAIClient` 추상화 및 개별 구현체.

## 사용법(Usage)
```python
from common_lib.config import Settings
from common_lib.db import get_session
from common_lib.ai_clients import ClaudeClient

settings = Settings()  # .env 파일 자동 로드
client = ClaudeClient(api_key=settings.claude_api_key)
```

## 테스트(Testing)
- 단위 테스트 예시(Unit test example):
  ```bash
  pytest tests/common_lib  # 향후 테스트 케이스 추가 예정
  ```
- 로거 확인(Logger verification):
  ```bash
  python - <<'PY'
  from common_lib.logger import get_logger
  logger = get_logger("demo")
  logger.info("CommonLib logger ready")
  PY
  ```

## Docker(Usage in Docker)
- 개별 서비스 Dockerfile 에서 `pip install -e ../common_lib` 형태로 의존성 주입 가능.

