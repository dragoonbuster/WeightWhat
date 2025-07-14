"""
Error response models for SizeComparator aligned with ERROR_MONITORING_SPEC.

This module contains all error response models with standardized taxonomy
for monitoring and operational excellence.
"""

from pydantic import BaseModel, Field, model_validator, ConfigDict
from typing import Optional, List, Dict, Any, Union, Literal
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum
import traceback
import os


class ErrorCategory(str, Enum):
    """Error categories aligned with ERROR_MONITORING_SPEC."""
    CLIENT_ERROR = "client_error"          # 4xx errors - user input issues
    SERVER_ERROR = "server_error"          # 5xx errors - internal failures
    INTEGRATION_ERROR = "integration_error" # External API failures
    BUSINESS_LOGIC_ERROR = "business_logic_error" # Validation/constraint violations


class ErrorSeverity(str, Enum):
    """Error severity levels from ERROR_MONITORING_SPEC."""
    CRITICAL = "critical"  # System outage, immediate intervention required
    WARNING = "warning"    # Degraded performance, notify on-call team
    INFO = "info"         # Anomalies worth investigating, no immediate action


class FieldError(BaseModel):
    """Individual field validation error."""
    field_path: str = Field(
        ...,
        description="JSONPath to the field with error",
        examples=["item1_weight.value", "request.ai_temperature"]
    )
    error_code: str = Field(
        ...,
        pattern=r'^[A-Z][A-Z0-9_]+$',
        description="Machine-readable error code"
    )
    error_message: str = Field(
        ...,
        description="Human-readable error description"
    )
    invalid_value: Optional[Any] = Field(
        None,
        description="The invalid value that caused the error"
    )
    constraint_violated: Optional[str] = Field(
        None,
        description="Validation constraint that was violated"
    )
    suggested_fix: Optional[str] = Field(
        None,
        description="Suggested correction for the error"
    )


class ErrorContext(BaseModel):
    """Additional context for error investigation."""
    component: str = Field(
        ...,
        description="System component where error occurred",
        examples=["api", "weight_processor", "ai_provider", "cache"]
    )
    operation: str = Field(
        ...,
        description="Operation being performed when error occurred"
    )
    user_agent: Optional[str] = Field(
        None,
        max_length=500,
        description="Client user agent string"
    )
    ip_address: Optional[str] = Field(
        None,
        pattern=r'^(\d{1,3}\.){3}\d{1,3}$|^[a-fA-F0-9:]+$',
        description="Client IP address (anonymized)"
    )
    session_id: Optional[str] = Field(
        None,
        description="User session identifier"
    )
    correlation_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional correlation data"
    )


class BaseErrorResponse(BaseModel):
    """Base error response model for ERROR_MONITORING_SPEC compliance."""
    error_id: UUID = Field(
        default_factory=uuid4,
        description="Unique error identifier for tracking"
    )
    error_code: str = Field(
        ...,
        pattern=r'^[A-Z][A-Z0-9_]+$',
        description="Machine-readable error code"
    )
    error_category: ErrorCategory = Field(
        ...,
        description="Error classification for monitoring"
    )
    severity: ErrorSeverity = Field(
        ...,
        description="Error severity level"
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Human-readable error message"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )
    request_id: UUID = Field(
        ...,
        description="Request correlation ID from BACKEND_CORE_SPEC"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error occurrence timestamp"
    )
    context: Optional[ErrorContext] = Field(
        None,
        description="Error context for investigation"
    )
    remediation_hint: Optional[str] = Field(
        None,
        max_length=500,
        description="Suggested remediation steps"
    )
    documentation_url: Optional[str] = Field(
        None,
        pattern=r'^https?://.*',
        description="Link to relevant documentation"
    )


class ValidationErrorResponse(BaseErrorResponse):
    """Validation error with field-specific details."""
    error_category: Literal[ErrorCategory.CLIENT_ERROR] = Field(
        default=ErrorCategory.CLIENT_ERROR,
        description="Always client error for validation failures"
    )
    field_errors: List[FieldError] = Field(
        default_factory=list,
        max_items=50,
        description="Detailed field validation errors"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error_id": "550e8400-e29b-41d4-a716-446655440000",
                "error_code": "VALIDATION_FAILED",
                "error_category": "client_error",
                "severity": "info",
                "message": "Request validation failed",
                "request_id": "660e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2025-07-13T10:30:00Z",
                "field_errors": [
                    {
                        "field_path": "item1_weight.value",
                        "error_code": "INVALID_WEIGHT_FORMAT",
                        "error_message": "Weight must be positive number",
                        "invalid_value": "-5",
                        "constraint_violated": "minimum",
                        "suggested_fix": "Provide a positive weight value"
                    }
                ],
                "remediation_hint": "Please check the field errors and correct your input",
                "documentation_url": "https://docs.sizecomparator.com/errors/validation"
            }
        }
    )


class BusinessLogicErrorResponse(BaseErrorResponse):
    """Business logic violation errors."""
    error_category: Literal[ErrorCategory.BUSINESS_LOGIC_ERROR] = Field(
        default=ErrorCategory.BUSINESS_LOGIC_ERROR,
        description="Business logic constraint violation"
    )
    constraint_type: str = Field(
        ...,
        description="Type of business constraint violated",
        examples=["comparison_limit", "weight_range", "item_restriction"]
    )
    constraint_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Details about the violated constraint"
    )


class IntegrationErrorResponse(BaseErrorResponse):
    """External service integration errors."""
    error_category: Literal[ErrorCategory.INTEGRATION_ERROR] = Field(
        default=ErrorCategory.INTEGRATION_ERROR,
        description="External service failure"
    )
    service_name: str = Field(
        ...,
        description="Name of the failing external service",
        examples=["openai", "anthropic", "xai", "redis"]
    )
    service_status: str = Field(
        ...,
        description="Status of the external service",
        examples=["timeout", "rate_limited", "authentication_failed", "circuit_open"]
    )
    retry_after_seconds: Optional[int] = Field(
        None,
        ge=0,
        le=3600,
        description="Suggested retry delay in seconds"
    )
    fallback_available: bool = Field(
        False,
        description="Whether fallback service is available"
    )
    fallback_service: Optional[str] = Field(
        None,
        description="Name of fallback service if available"
    )


class ServerErrorResponse(BaseErrorResponse):
    """Internal server errors."""
    error_category: Literal[ErrorCategory.SERVER_ERROR] = Field(
        default=ErrorCategory.SERVER_ERROR,
        description="Internal server failure"
    )
    incident_id: Optional[str] = Field(
        None,
        description="Incident tracking identifier"
    )
    estimated_fix_time: Optional[datetime] = Field(
        None,
        description="Estimated fix time if known"
    )
    stack_trace: Optional[str] = Field(
        None,
        description="Stack trace (only in development mode)"
    )
    
    @model_validator(mode='after')
    def remove_sensitive_data_in_production(self) -> 'ServerErrorResponse':
        """Remove sensitive data in production."""
        if os.getenv('SIZECOMPARATOR_ENV') == 'production':
            self.stack_trace = None
            if self.details:
                # Remove any sensitive keys
                sensitive_keys = ['password', 'api_key', 'secret', 'token']
                self.details = {
                    k: v for k, v in self.details.items() 
                    if not any(sensitive in k.lower() for sensitive in sensitive_keys)
                }
        return self


class ErrorFactory:
    """Factory for creating standardized error responses."""
    
    @staticmethod
    def validation_error(
        field_errors: List[FieldError],
        request_id: UUID,
        message: Optional[str] = None
    ) -> ValidationErrorResponse:
        """Create validation error response."""
        return ValidationErrorResponse(
            error_code="VALIDATION_FAILED",
            severity=ErrorSeverity.INFO,
            message=message or f"Validation failed for {len(field_errors)} field(s)",
            request_id=request_id,
            field_errors=field_errors,
            remediation_hint="Please check the field errors and correct your input",
            documentation_url="https://docs.sizecomparator.com/errors/validation"
        )
    
    @staticmethod
    def integration_error(
        service_name: str,
        service_status: str,
        request_id: UUID,
        retry_after: Optional[int] = None,
        fallback_service: Optional[str] = None
    ) -> IntegrationErrorResponse:
        """Create integration error response."""
        error_codes = {
            "timeout": "SERVICE_TIMEOUT",
            "rate_limited": "RATE_LIMIT_EXCEEDED",
            "authentication_failed": "AUTH_FAILED",
            "circuit_open": "CIRCUIT_BREAKER_OPEN"
        }
        
        return IntegrationErrorResponse(
            error_code=error_codes.get(service_status, "INTEGRATION_ERROR"),
            severity=ErrorSeverity.WARNING if fallback_service else ErrorSeverity.CRITICAL,
            message=f"{service_name} service {service_status}",
            request_id=request_id,
            service_name=service_name,
            service_status=service_status,
            retry_after_seconds=retry_after,
            fallback_available=bool(fallback_service),
            fallback_service=fallback_service,
            remediation_hint=f"Using fallback service: {fallback_service}" if fallback_service else "Please try again later"
        )
    
    @staticmethod
    def server_error(
        error: Exception,
        request_id: UUID,
        component: str,
        operation: str
    ) -> ServerErrorResponse:
        """Create server error response."""
        response = ServerErrorResponse(
            error_code="INTERNAL_SERVER_ERROR",
            severity=ErrorSeverity.CRITICAL,
            message="An internal error occurred",
            request_id=request_id,
            context=ErrorContext(
                component=component,
                operation=operation
            ),
            remediation_hint="Our team has been notified. Please try again later."
        )
        
        # Add stack trace in development
        if os.getenv('SIZECOMPARATOR_ENV') == 'development':
            response.stack_trace = traceback.format_exc()
            response.message = str(error)
        
        return response
    
    @staticmethod
    def business_logic_error(
        constraint_type: str,
        message: str,
        request_id: UUID,
        constraint_details: Optional[Dict[str, Any]] = None
    ) -> BusinessLogicErrorResponse:
        """Create business logic error response."""
        return BusinessLogicErrorResponse(
            error_code="BUSINESS_CONSTRAINT_VIOLATED",
            severity=ErrorSeverity.INFO,
            message=message,
            request_id=request_id,
            constraint_type=constraint_type,
            constraint_details=constraint_details or {},
            remediation_hint="Please review the constraint details and adjust your request"
        )