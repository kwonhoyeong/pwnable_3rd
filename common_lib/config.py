"""공통 설정 모듈(Common configuration module)."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """시스템 환경설정(System environment settings)."""

    app_name: str = Field(default="npm-threat-evaluator", description="서비스 이름(Service name)")
    environment: str = Field(default="development", description="실행 환경(Runtime environment)")

    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/threatdb.sqlite",
        description="데이터베이스 연결 URL(Database connection URL)",
    )
    cache_ttl: int = Field(default=3600, description="캐시 TTL(초)(Cache TTL in seconds)")
    kafka_bootstrap_servers: str = Field(
        default="kafka:9092",
        description="Kafka 부트스트랩 서버(Kafka bootstrap servers)",
    )

    perplexity_api_key: str = Field(default="", description="Perplexity API 키(Perplexity API key)")
    claude_api_key: str = Field(default="", description="Claude API 키(Claude API key)")
    gpt5_api_key: str = Field(default="", description="GPT-5 API 키(GPT-5 API key)")

    log_level: str = Field(default="INFO", description="로그 레벨(Log level)")

    model_config = {
        "env_prefix": "NT_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache(maxsize=1)
def get_settings(overrides: Dict[str, Any] | None = None) -> Settings:
    """설정 인스턴스 반환(Return a cached settings instance)."""

    if overrides:
        return Settings(**overrides)
    return Settings()


def load_environment() -> None:
    """기본 환경변수를 로드(Load base environment variables)."""

    os.environ.setdefault("TZ", "UTC")

