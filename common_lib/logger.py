"""공통 로깅 유틸리티(Common logging utilities)."""
from __future__ import annotations

import logging
from logging import Logger

from .config import get_settings


def configure_logging() -> None:
    """전역 로거 설정(Set up global logger)."""

    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def get_logger(name: str) -> Logger:
    """명명된 로거 가져오기(Get a named logger)."""

    configure_logging()
    return logging.getLogger(name)

