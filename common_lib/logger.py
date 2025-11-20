import logging
import sys

_logging_configured = False

def setup_logging():
    global _logging_configured
    if _logging_configured:
        return

    # 가장 단순하고 안전한 기본 설정 (JSON 아님)
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        stream=sys.stdout,
        force=True  # 기존 설정 강제 덮어쓰기
    )

    # 라이브러리 로그 레벨 조정
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    _logging_configured = True


def get_logger(name: str):
    """명명된 로거 가져오기(Get a named logger).

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    setup_logging()
    return logging.getLogger(name)