"""엔터프라이즈 관찰성 및 구조화 로깅(Enterprise observability and structured logging)."""
from __future__ import annotations

import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict

from pythonjsonlogger import jsonlogger

# Context variable to store request ID for distributed tracing
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="system")


def get_request_id() -> str:
    """요청 ID 조회(Retrieve the current request ID).

    Returns:
        Current request ID from context, or "system" if not set.
    """
    return request_id_ctx.get()


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """사용자 정의 JSON 포매터(Custom JSON formatter with request ID injection).

    Extends pythonjsonlogger.JsonFormatter to inject request_id
    and manually handle all field creation to avoid KeyErrors.
    """

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """
        필드 추가 및 요청 ID 삽입(Add fields and inject request ID).

        Manually handles all field creation to avoid KeyErrors from
        pythonjsonlogger's field renaming logic.

        Args:
            log_record: The log record dictionary
            record: The LogRecord object
            message_dict: The message dictionary
        """
        # Call parent first
        super().add_fields(log_record, record, message_dict)

        # Manually add timestamp in ISO8601 format (don't rely on library)
        if "timestamp" not in log_record:
            # Create timestamp using timezone-aware UTC (avoids deprecation warning)
            now = datetime.now(timezone.utc).isoformat()
            log_record["timestamp"] = now

        # Remove asctime if present (we use timestamp instead)
        log_record.pop("asctime", None)

        # Inject request ID from context
        log_record["request_id"] = get_request_id()

        # Ensure level/levelname is present
        if "level" not in log_record:
            log_record["level"] = record.levelname

        # Ensure message is present
        if "message" not in log_record:
            log_record["message"] = record.getMessage()

        # Ensure name (logger name) is present
        if "name" not in log_record:
            log_record["name"] = record.name
