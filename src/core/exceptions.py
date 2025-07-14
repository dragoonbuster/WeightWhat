"""
Error handling and exception classes for SizeComparator.

Implements ERROR_MONITORING_SPEC error categorization aligned with BACKEND_CORE_SPEC
ErrorCategory enum and provides structured error responses with monitoring integration.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .monitoring import ErrorCategory, ErrorSeverity, request_context


class ErrorResponse(BaseModel):
    """
    Standardized error response matching ERROR_MONITORING_SPEC.
    
    Aligns with BACKEND_CORE_SPEC ErrorResponse model for consistent
    error handling across all components.
    """
    error_code: str = Field(..., description="Unique error identifier")
    error_category: ErrorCategory = Field(..., description="Error classification")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    request_id: str = Field(..., description="Correlation ID for tracing")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    severity: ErrorSeverity = Field(..., description="Alert severity level")
    remediation_hint: Optional[str] = Field(None, description="Suggested fix")


class ValidationErrorResponse(ErrorResponse):
    """Specific error response for validation failures."""
    error_category: ErrorCategory = Field(default=ErrorCategory.CLIENT_ERROR)
    field_errors: List[Dict[str, str]] = Field(default_factory=list)


class SizeComparatorException(Exception):
    """
    Base exception class for SizeComparator with monitoring integration.
    
    All custom exceptions inherit from this class to ensure consistent
    error categorization and monitoring integration.
    """
    
    category: ErrorCategory = ErrorCategory.SERVER_ERROR
    severity: ErrorSeverity = ErrorSeverity.WARNING
    error_code: str = "UNKNOWN_ERROR"
    remediation_hint: Optional[str] = None
    
    def __init__(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.request_id = request_id or request_context.get_request_id() or "unknown"
        self.timestamp = datetime.now(timezone.utc)
    
    def to_error_response(self) -> ErrorResponse:
        """Convert exception to standardized error response."""
        return ErrorResponse(
            error_code=self.error_code,
            error_category=self.category,
            message=self.message,
            details=self.details,
            request_id=self.request_id,
            timestamp=self.timestamp,
            severity=self.severity,
            remediation_hint=self.remediation_hint
        )
    
    def get_http_status_code(self) -> int:
        """Get appropriate HTTP status code for this error category."""
        status_mapping = {
            ErrorCategory.CLIENT_ERROR: 400,
            ErrorCategory.BUSINESS_LOGIC_ERROR: 422,
            ErrorCategory.INTEGRATION_ERROR: 503,
            ErrorCategory.SERVER_ERROR: 500
        }
        return status_mapping.get(self.category, 500)


# CLIENT_ERROR exceptions (4xx responses)
class ValidationException(SizeComparatorException):
    """Client error for request validation failures."""
    category = ErrorCategory.CLIENT_ERROR
    severity = ErrorSeverity.INFO
    error_code = "VALIDATION_ERROR"
    remediation_hint = "Check request format and required fields"
    
    def __init__(
        self, 
        message: str, 
        field_errors: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.field_errors = field_errors or []
    
    def to_error_response(self) -> ValidationErrorResponse:
        """Convert to validation-specific error response."""
        return ValidationErrorResponse(
            error_code=self.error_code,
            error_category=self.category,
            message=self.message,
            details=self.details,
            request_id=self.request_id,
            timestamp=self.timestamp,
            severity=self.severity,
            remediation_hint=self.remediation_hint,
            field_errors=self.field_errors
        )


class AuthenticationException(SizeComparatorException):
    """Client error for authentication failures."""
    category = ErrorCategory.CLIENT_ERROR
    severity = ErrorSeverity.WARNING
    error_code = "AUTHENTICATION_ERROR"
    remediation_hint = "Verify API credentials and authentication headers"


class AuthorizationException(SizeComparatorException):
    """Client error for authorization failures."""
    category = ErrorCategory.CLIENT_ERROR
    severity = ErrorSeverity.WARNING
    error_code = "AUTHORIZATION_ERROR"
    remediation_hint = "Check user permissions for this operation"


class RateLimitException(SizeComparatorException):
    """Client error for rate limiting."""
    category = ErrorCategory.CLIENT_ERROR
    severity = ErrorSeverity.INFO
    error_code = "RATE_LIMIT_EXCEEDED"
    remediation_hint = "Reduce request rate and implement exponential backoff"


# BUSINESS_LOGIC_ERROR exceptions (422 responses)
class WeightParsingException(SizeComparatorException):
    """Business logic error for invalid weight formats."""
    category = ErrorCategory.BUSINESS_LOGIC_ERROR
    severity = ErrorSeverity.WARNING
    error_code = "WEIGHT_PARSING_ERROR"
    remediation_hint = "Provide weight in format like '5 kg', '10 pounds', or '2.5 lbs'"


class UnitConversionException(SizeComparatorException):
    """Business logic error for unit conversion failures."""
    category = ErrorCategory.BUSINESS_LOGIC_ERROR
    severity = ErrorSeverity.WARNING
    error_code = "UNIT_CONVERSION_ERROR"
    remediation_hint = "Ensure valid weight units (kg, lb, oz, g, st, mt)"


class WeightValidationException(SizeComparatorException):
    """Business logic error for weight constraint violations."""
    category = ErrorCategory.BUSINESS_LOGIC_ERROR
    severity = ErrorSeverity.WARNING
    error_code = "WEIGHT_VALIDATION_ERROR"
    remediation_hint = "Weight must be between 0.001 kg and 1,000,000 kg"


class ComparisonLogicException(SizeComparatorException):
    """Business logic error for comparison logic errors."""
    category = ErrorCategory.BUSINESS_LOGIC_ERROR
    severity = ErrorSeverity.WARNING
    error_code = "COMPARISON_LOGIC_ERROR"
    remediation_hint = "Ensure both items have valid weights for comparison"


class TemplateRenderingException(SizeComparatorException):
    """Business logic error for template rendering failures."""
    category = ErrorCategory.BUSINESS_LOGIC_ERROR
    severity = ErrorSeverity.WARNING
    error_code = "TEMPLATE_RENDERING_ERROR"
    remediation_hint = "Check template format and provided context variables"


# INTEGRATION_ERROR exceptions (503 responses)
class AIProviderException(SizeComparatorException):
    """Integration error for AI service failures."""
    category = ErrorCategory.INTEGRATION_ERROR
    severity = ErrorSeverity.CRITICAL
    error_code = "AI_PROVIDER_ERROR"
    remediation_hint = "Check AI provider status and API connectivity"


class AIProviderTimeoutException(AIProviderException):
    """Integration error for AI provider timeouts."""
    error_code = "AI_PROVIDER_TIMEOUT"
    remediation_hint = "AI provider response timeout - try again or use fallback provider"


class AIProviderRateLimitException(AIProviderException):
    """Integration error for AI provider rate limiting."""
    error_code = "AI_PROVIDER_RATE_LIMIT"
    severity = ErrorSeverity.WARNING
    remediation_hint = "AI provider rate limit reached - implement exponential backoff"


class CircuitBreakerOpenException(AIProviderException):
    """Integration error for circuit breaker open state."""
    error_code = "CIRCUIT_BREAKER_OPEN"
    severity = ErrorSeverity.CRITICAL
    remediation_hint = "AI provider circuit breaker is open - use fallback provider"


class ProviderNotFoundException(AIProviderException):
    """Integration error for missing provider."""
    error_code = "PROVIDER_NOT_FOUND"
    severity = ErrorSeverity.CRITICAL
    remediation_hint = "Ensure provider is registered and available"


class ConfigurationException(SizeComparatorException):
    """Configuration error for invalid configuration."""
    category = ErrorCategory.SERVER_ERROR
    severity = ErrorSeverity.CRITICAL
    error_code = "CONFIGURATION_EXCEPTION"
    remediation_hint = "Check configuration format and required fields"


class ExternalAPIException(SizeComparatorException):
    """Integration error for external API failures."""
    category = ErrorCategory.INTEGRATION_ERROR
    severity = ErrorSeverity.WARNING
    error_code = "EXTERNAL_API_ERROR"
    remediation_hint = "Check external service status and network connectivity"


class CacheException(SizeComparatorException):
    """Integration error for cache service failures."""
    category = ErrorCategory.INTEGRATION_ERROR
    severity = ErrorSeverity.WARNING
    error_code = "CACHE_ERROR"
    remediation_hint = "Cache service unavailable - operation will proceed without caching"


class NetworkConnectivityException(SizeComparatorException):
    """Integration error for network connectivity issues."""
    category = ErrorCategory.INTEGRATION_ERROR
    severity = ErrorSeverity.CRITICAL
    error_code = "NETWORK_CONNECTIVITY_ERROR"
    remediation_hint = "Check network connectivity and firewall settings"


# SERVER_ERROR exceptions (5xx responses)
class InternalServerError(SizeComparatorException):
    """Server error for internal system failures."""
    category = ErrorCategory.SERVER_ERROR
    severity = ErrorSeverity.CRITICAL
    error_code = "INTERNAL_SERVER_ERROR"
    remediation_hint = "Internal server error - contact system administrator"


class ConfigurationError(SizeComparatorException):
    """Server error for configuration issues."""
    category = ErrorCategory.SERVER_ERROR
    severity = ErrorSeverity.CRITICAL
    error_code = "CONFIGURATION_ERROR"
    remediation_hint = "Check application configuration and environment variables"


class ServiceUnavailableException(SizeComparatorException):
    """Server error for service unavailability."""
    category = ErrorCategory.SERVER_ERROR
    severity = ErrorSeverity.CRITICAL
    error_code = "SERVICE_UNAVAILABLE"
    remediation_hint = "Service temporarily unavailable - try again later"


class DatabaseException(SizeComparatorException):
    """Server error for database failures."""
    category = ErrorCategory.SERVER_ERROR
    severity = ErrorSeverity.CRITICAL
    error_code = "DATABASE_ERROR"
    remediation_hint = "Database connectivity issue - check database status"


class MemoryLimitException(SizeComparatorException):
    """Server error for memory limit breaches."""
    category = ErrorCategory.SERVER_ERROR
    severity = ErrorSeverity.CRITICAL
    error_code = "MEMORY_LIMIT_EXCEEDED"
    remediation_hint = "System memory limit exceeded - scale resources or optimize processing"


class ResourceExhaustionException(SizeComparatorException):
    """Server error for resource exhaustion."""
    category = ErrorCategory.SERVER_ERROR
    severity = ErrorSeverity.CRITICAL
    error_code = "RESOURCE_EXHAUSTION"
    remediation_hint = "System resources exhausted - scale infrastructure or reduce load"


# Error mapping for automatic categorization
ERROR_CATEGORY_MAPPING = {
    # Client errors
    ValidationException: ErrorCategory.CLIENT_ERROR,
    AuthenticationException: ErrorCategory.CLIENT_ERROR,
    AuthorizationException: ErrorCategory.CLIENT_ERROR,
    RateLimitException: ErrorCategory.CLIENT_ERROR,
    
    # Business logic errors
    WeightParsingException: ErrorCategory.BUSINESS_LOGIC_ERROR,
    UnitConversionException: ErrorCategory.BUSINESS_LOGIC_ERROR,
    WeightValidationException: ErrorCategory.BUSINESS_LOGIC_ERROR,
    ComparisonLogicException: ErrorCategory.BUSINESS_LOGIC_ERROR,
    TemplateRenderingException: ErrorCategory.BUSINESS_LOGIC_ERROR,
    
    # Integration errors
    AIProviderException: ErrorCategory.INTEGRATION_ERROR,
    AIProviderTimeoutException: ErrorCategory.INTEGRATION_ERROR,
    AIProviderRateLimitException: ErrorCategory.INTEGRATION_ERROR,
    CircuitBreakerOpenException: ErrorCategory.INTEGRATION_ERROR,
    ExternalAPIException: ErrorCategory.INTEGRATION_ERROR,
    CacheException: ErrorCategory.INTEGRATION_ERROR,
    NetworkConnectivityException: ErrorCategory.INTEGRATION_ERROR,
    
    # Server errors
    InternalServerError: ErrorCategory.SERVER_ERROR,
    ConfigurationError: ErrorCategory.SERVER_ERROR,
    ServiceUnavailableException: ErrorCategory.SERVER_ERROR,
    DatabaseException: ErrorCategory.SERVER_ERROR,
    MemoryLimitException: ErrorCategory.SERVER_ERROR,
    ResourceExhaustionException: ErrorCategory.SERVER_ERROR,
}


def map_exception_to_error_response(
    exc: Exception, 
    request_id: Optional[str] = None
) -> ErrorResponse:
    """
    Convert any exception to standardized ErrorResponse.
    
    For SizeComparatorException instances, uses their built-in categorization.
    For other exceptions, maps to appropriate category based on type.
    """
    if isinstance(exc, SizeComparatorException):
        return exc.to_error_response()
    
    # Map standard Python exceptions to categories
    category = ErrorCategory.SERVER_ERROR
    severity = ErrorSeverity.WARNING
    error_code = f"STANDARD_{exc.__class__.__name__.upper()}"
    remediation_hint = None
    
    if isinstance(exc, ValueError):
        category = ErrorCategory.CLIENT_ERROR
        severity = ErrorSeverity.INFO
        remediation_hint = "Check input values and format"
    elif isinstance(exc, TypeError):
        category = ErrorCategory.CLIENT_ERROR
        severity = ErrorSeverity.INFO
        remediation_hint = "Check input types and structure"
    elif isinstance(exc, KeyError):
        category = ErrorCategory.BUSINESS_LOGIC_ERROR
        severity = ErrorSeverity.WARNING
        remediation_hint = "Required field or key is missing"
    elif isinstance(exc, TimeoutError):
        category = ErrorCategory.INTEGRATION_ERROR
        severity = ErrorSeverity.WARNING
        remediation_hint = "Operation timed out - try again or check service status"
    elif isinstance(exc, ConnectionError):
        category = ErrorCategory.INTEGRATION_ERROR
        severity = ErrorSeverity.CRITICAL
        remediation_hint = "Connection failed - check network connectivity"
    elif isinstance(exc, MemoryError):
        category = ErrorCategory.SERVER_ERROR
        severity = ErrorSeverity.CRITICAL
        remediation_hint = "System out of memory - scale resources"
    
    return ErrorResponse(
        error_code=error_code,
        error_category=category,
        message=str(exc),
        request_id=request_id or request_context.get_request_id() or "unknown",
        severity=severity,
        remediation_hint=remediation_hint
    )


def get_remediation_hint(exception_class: type) -> Optional[str]:
    """Get remediation hint for exception class."""
    if hasattr(exception_class, 'remediation_hint'):
        return exception_class.remediation_hint
    
    # Default hints for common exceptions
    remediation_hints = {
        ValueError: "Check input values and format",
        TypeError: "Check input types and structure", 
        KeyError: "Required field or key is missing",
        TimeoutError: "Operation timed out - try again or check service status",
        ConnectionError: "Connection failed - check network connectivity",
        MemoryError: "System out of memory - scale resources"
    }
    
    return remediation_hints.get(exception_class)


class ErrorHandler:
    """
    Centralized error handler for consistent error processing.
    
    Integrates with monitoring system for error tracking and alerting.
    """
    
    def __init__(self, metrics_collector, logger):
        self.metrics = metrics_collector
        self.logger = logger
    
    def handle_exception(
        self, 
        exc: Exception,
        endpoint: str = "unknown",
        request_id: Optional[str] = None
    ) -> ErrorResponse:
        """
        Handle exception with monitoring integration.
        
        Records error metrics, logs error details, and returns
        standardized error response.
        """
        error_response = map_exception_to_error_response(exc, request_id)
        
        # Record error metrics
        self.metrics.record_error(
            error_category=error_response.error_category.value,
            error_code=error_response.error_code,
            endpoint=endpoint
        )
        
        # Log error with context
        log_context = {
            'error_code': error_response.error_code,
            'error_category': error_response.error_category.value,
            'severity': error_response.severity.value,
            'endpoint': endpoint,
            'details': error_response.details
        }
        
        if error_response.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(error_response.message, **log_context)
        elif error_response.severity == ErrorSeverity.WARNING:
            self.logger.warning(error_response.message, **log_context)
        else:
            self.logger.info(error_response.message, **log_context)
        
        return error_response


# Retry strategies for different error categories
class RetryStrategy:
    """Retry strategy configuration for different error categories."""
    
    @staticmethod
    def get_retry_config(error_category: ErrorCategory) -> Dict[str, Any]:
        """Get retry configuration for error category."""
        retry_configs = {
            ErrorCategory.CLIENT_ERROR: {
                'max_attempts': 1,  # Don't retry client errors
                'backoff_factor': 0,
                'jitter': False
            },
            ErrorCategory.BUSINESS_LOGIC_ERROR: {
                'max_attempts': 2,  # Limited retry for business logic
                'backoff_factor': 1,
                'jitter': True
            },
            ErrorCategory.INTEGRATION_ERROR: {
                'max_attempts': 3,  # Retry integration errors
                'backoff_factor': 2,
                'jitter': True,
                'timeout_multiplier': 1.5
            },
            ErrorCategory.SERVER_ERROR: {
                'max_attempts': 2,  # Limited retry for server errors
                'backoff_factor': 2,
                'jitter': True
            }
        }
        
        return retry_configs.get(error_category, retry_configs[ErrorCategory.SERVER_ERROR])