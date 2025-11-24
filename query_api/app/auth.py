"""QueryAPI 인증 및 인가 레이어(QueryAPI authentication and authorization layer)."""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from common_lib.config import get_settings
from common_lib.logger import get_logger

logger = get_logger(__name__)

# Security scheme for FastAPI documentation and validation
security = APIKeyHeader(
    name="X-API-Key",
    description="API Key for accessing QueryAPI endpoints",
    auto_error=False,  # Don't auto-raise 403, we'll handle custom responses
)


async def verify_api_key(
    api_key: Optional[str] = Depends(security),
) -> str:
    """API 키 검증(Verify API key from request).

    Args:
        api_key: API key from request header

    Returns:
        Verified API key string

    Raises:
        HTTPException: If authentication fails
    """
    # Check if credentials were provided
    if api_key is None:
        logger.warning("Request rejected: Missing API key in X-API-Key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide via X-API-Key header",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Get valid API keys from settings
    settings = get_settings()
    valid_api_keys = settings.query_api_keys

    # Validate that API keys are configured
    if not valid_api_keys:
        logger.error("No API keys configured in environment. Set QUERY_API_KEYS")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error: API keys not configured",
        )

    # Extract the token
    provided_key = api_key.strip()

    # Verify the API key is in the list of valid keys
    if provided_key not in valid_api_keys:
        logger.warning(
            "Request rejected: Invalid API key provided",
            extra={"key_prefix": provided_key[:5] if provided_key else "empty"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug("Request authenticated successfully")
    return provided_key


async def verify_api_key_optional(
    api_key: Optional[str] = Depends(security),
) -> Optional[str]:
    """선택적 API 키 검증(Optional API key verification for public endpoints).

    Args:
        api_key: API key from request header (optional)

    Returns:
        API key string if provided and valid, None if not provided
    """
    if api_key is None:
        return None

    # Get valid API keys from settings
    settings = get_settings()
    valid_api_keys = settings.query_api_keys

    if not valid_api_keys:
        logger.warning("No API keys configured, allowing unauthenticated access")
        return None

    provided_key = api_key.strip()

    # Verify the API key if provided
    if provided_key not in valid_api_keys:
        logger.warning(
            "Request with invalid API key rejected",
            extra={"key_prefix": provided_key[:5] if provided_key else "empty"},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug("Request authenticated with valid API key")
    return provided_key
