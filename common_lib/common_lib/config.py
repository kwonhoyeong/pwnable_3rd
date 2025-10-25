"""공통 설정 모듈(Common configuration module)."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Dict

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """시스템 환경설정(System environment settings)."""

    app_name: str = Field(default="npm-threat-evaluator", description="서비스 이름(Service name)")
    environment: str = Field(default="development", description="실행 환경(Runtime environment)")

    postgres_dsn: str = Field(
        default="postgresql+asyncpg://user:password@db:5432/threatdb",
        description="PostgreSQL 연결 DSN(PostgreSQL connection DSN)",
    )
    redis_url: str = Field(default="redis://redis:6379/0", description="Redis 접속 URL(Redis connection URL)")
    kafka_bootstrap_servers: str = Field(
        default="kafka:9092",
        description="Kafka 부트스트랩 서버(Kafka bootstrap servers)",
    )

    perplexity_api_key: str = Field(default="", description="Perplexity API 키(Perplexity API key)")
    claude_api_key: str = Field(default="", description="Claude API 키(Claude API key)")
    gpt5_api_key: str = Field(default="", description="GPT-5 API 키(GPT-5 API key)")

    log_level: str = Field(default="INFO", description="로그 레벨(Log level)")

    class Config:
        env_prefix = "NT_"
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache(maxsize=1)
def _load_settings() -> Settings:
    """환경 변수 기반 기본 설정을 로드(Load base settings from env)."""

    return Settings()


def get_settings(overrides: Dict[str, Any] | None = None) -> Settings:
    """설정 인스턴스 반환(Return a cached settings instance)."""

    if overrides:
        return Settings(**overrides)
    return _load_settings()


def load_environment() -> None:
    """기본 환경변수를 로드(Load base environment variables)."""

    os.environ.setdefault("TZ", "UTC")
