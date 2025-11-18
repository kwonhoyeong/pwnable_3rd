"""Custom exception types for the CVE analysis pipeline.

This module defines exceptions used throughout the pipeline to provide
clear error classification and recovery strategies.
"""


class PipelineError(Exception):
    """Base exception for pipeline-related errors."""

    pass


class ExternalAPIError(PipelineError):
    """
    Raised when an external API call (OSV, Perplexity, Claude, etc.) fails.

    This error indicates a transient or permanent failure to reach an external service.
    The pipeline should use fallback data when this error occurs.
    """

    def __init__(self, service: str, status_code: int = None, message: str = None):
        """
        Initialize ExternalAPIError.

        Args:
            service: Name of the external service (e.g., 'OSV', 'Perplexity')
            status_code: HTTP status code (if applicable)
            message: Optional additional error details
        """
        self.service = service
        self.status_code = status_code
        self.message = message

        msg = f"External API error: {service}"
        if status_code:
            msg += f" (HTTP {status_code})"
        if message:
            msg += f": {message}"

        super().__init__(msg)


class DataValidationError(PipelineError):
    """
    Raised when input data validation fails.

    This error indicates that input data (CVE ID format, package name, etc.)
    does not meet required constraints. The pipeline should reject the input
    rather than use fallback data.
    """

    def __init__(self, field: str, value: str, reason: str):
        """
        Initialize DataValidationError.

        Args:
            field: Name of the field that failed validation
            value: The invalid value
            reason: Why the value is invalid
        """
        self.field = field
        self.value = value
        self.reason = reason
        msg = f"Data validation error: {field}={value!r}. Reason: {reason}"
        super().__init__(msg)


class FallbackError(PipelineError):
    """
    Raised when fallback data generation itself fails.

    This is an exceptional case and indicates a serious problem
    that requires manual intervention.
    """

    def __init__(self, context: str, reason: str):
        """
        Initialize FallbackError.

        Args:
            context: What was being attempted (e.g., 'generating EPSS fallback')
            reason: Why it failed
        """
        self.context = context
        self.reason = reason
        msg = f"Fallback generation failed: {context}. Reason: {reason}"
        super().__init__(msg)
