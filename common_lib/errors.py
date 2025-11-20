"""공통 에러 클래스 정의(Common error classes)."""
from __future__ import annotations

from typing import Any, Dict, Optional


class AppException(Exception):
    """애플리케이션 기본 예외 클래스(Base application exception)."""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize exception with structured error information.

        Args:
            status_code: HTTP status code (e.g., 404, 503, 400)
            error_code: Machine-readable error code (e.g., "RESOURCE_NOT_FOUND")
            message: Human-readable error message
            details: Additional error context (optional)
        """
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        response: Dict[str, Any] = {
            "error": {
                "code": self.error_code,
                "message": self.message,
            }
        }
        if self.details:
            response["error"]["details"] = self.details
        return response


class ResourceNotFound(AppException):
    """자원을 찾을 수 없음(Resource not found - 404)."""

    def __init__(
        self,
        resource_type: str,
        identifier: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize with resource context.

        Args:
            resource_type: Type of resource (e.g., "package", "cve")
            identifier: Resource identifier (e.g., package name, CVE ID)
            details: Additional context
        """
        message = f"{resource_type.capitalize()} '{identifier}' not found."
        super().__init__(
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
            message=message,
            details=details or {"resource_type": resource_type, "identifier": identifier},
        )


class ExternalServiceError(AppException):
    """외부 서비스 오류(External service unavailable - 503)."""

    def __init__(
        self,
        service_name: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize with service context.

        Args:
            service_name: Name of the external service (e.g., "Database", "AI API")
            reason: Reason for the failure
            details: Additional context
        """
        message = f"{service_name} is currently unavailable: {reason}"
        super().__init__(
            status_code=503,
            error_code="EXTERNAL_SERVICE_ERROR",
            message=message,
            details=details or {"service_name": service_name, "reason": reason},
        )


class InvalidInputError(AppException):
    """유효하지 않은 입력(Invalid input - 400)."""

    def __init__(
        self,
        field: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize with validation context.

        Args:
            field: Field name that failed validation
            reason: Why the field is invalid
            details: Additional context
        """
        message = f"Invalid input for '{field}': {reason}"
        super().__init__(
            status_code=400,
            error_code="INVALID_INPUT",
            message=message,
            details=details or {"field": field, "reason": reason},
        )
