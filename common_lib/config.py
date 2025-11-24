"""공통 설정 모듈(Common configuration module)."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """시스템 환경설정(System environment settings)."""

    model_config = SettingsConfigDict(
        env_prefix="NT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="npm-threat-evaluator", description="서비스 이름(Service name)")
    environment: str = Field(default="development", description="실행 환경(Runtime environment)")

    postgres_dsn: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/threatdb",
        description="PostgreSQL 연결 DSN(PostgreSQL connection DSN)",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis 접속 URL(Redis connection URL)")
    cache_ttl_seconds: int | None = Field(
        default=3600,
        env="CACHE_TTL_SECONDS",
        description="Redis 캐시 TTL(Redis cache TTL in seconds)",
    )
    kafka_bootstrap_servers: str = Field(
        default="kafka:9092",
        description="Kafka 부트스트랩 서버(Kafka bootstrap servers)",
    )
    allow_external_calls: bool = Field(
        default=True,
        description="외부 API 호출 허용 여부(Allow outbound API calls in this environment)",
    )
    enable_database: bool = Field(
        default=False,
        description="PostgreSQL 지속성 사용 여부(Enable PostgreSQL persistence)",
    )
    enable_cache: bool = Field(
        default=False,
        description="Redis 캐시 사용 여부(Enable Redis caching)",
    )

    perplexity_api_key: str = Field(default="", description="Perplexity API 키(Perplexity API key)")
    claude_api_key: str = Field(default="", description="Claude API 키(Claude API key)")
    gpt5_api_key: str = Field(default="", description="GPT-5 API 키(GPT-5 API key)")
    nvd_api_key: str = Field(default="", description="NVD API 키(NVD API key)")

    query_api_keys: str | list[str] = Field(
        default_factory=list,
        env="QUERY_API_KEYS",
        description="QueryAPI 인증 키 쉼표 구분 목록(Comma-separated list of valid API keys for QueryAPI)",
    )

    log_level: str = Field(default="INFO", description="로그 레벨(Log level)")

    @field_validator("query_api_keys", mode="before")
    @classmethod
    def parse_query_api_keys(cls, v: Any) -> list[str]:
        """Parse comma-separated API keys string into list."""
        # logger is not available here easily as it might cause circular import or not initialized
        # print(f"DEBUG: parse_query_api_keys called with type={type(v)} value={v}")
        
        if v is None:
            return []
        if isinstance(v, str):
            # Handle potential JSON string representation if pydantic tries to be smart
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass # Fallback to comma split
            
            # Split by comma and strip whitespace
            return [key.strip() for key in v.split(",") if key.strip()]
        elif isinstance(v, list):
            return v
        return []


@lru_cache(maxsize=1)
def get_settings(overrides: Dict[str, Any] | None = None) -> Settings:
    """설정 인스턴스 반환(Return a cached settings instance)."""

    if overrides:
        return Settings(**overrides)
    return Settings()


def load_environment() -> None:
    """기본 환경변수를 로드(Load base environment variables)."""

    os.environ.setdefault("TZ", "UTC")
