"""
Global Error Handling Middleware

This middleware provides comprehensive error handling for ERROR_MONITORING_SPEC compliance:
- Catches and formats all unhandled exceptions
- Provides standardized error responses
- Logs errors with proper context
- Tracks error metrics
- Supports custom error types and HTTP status codes
"""

import json
import logging
import time
import traceback
from datetime import datetime
from typing import Callable, Any, Dict, Optional

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.middleware.base import BaseHTTPMiddleware

from ...models.errors import ErrorCategory, ErrorSeverity
from ...core.config import ConfigLoader
from .request_id import get_current_request_id

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware for standardized error responses.
    
    This middleware catches all unhandled exceptions and converts them
    to properly formatted JSON responses with appropriate HTTP status codes
    and ERROR_MONITORING_SPEC compliance.
    """
    
    def __init__(
        self,
        app,
        config_loader: ConfigLoader,
        include_debug_info: Optional[bool] = None,
        log_all_errors: bool = True
    ):
        super().__init__(app)
        self.config_loader = config_loader
        self.environment = config_loader.get_section("application.environment", "development")
        self.include_debug_info = include_debug_info if include_debug_info is not None else (self.environment != "production")
        self.log_all_errors = log_all_errors
        
        # Error tracking
        self.error_counts = {}
        
    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        """Process request with comprehensive error handling"""
        
        start_time = time.time()
        request_id = get_current_request_id() or "unknown"
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Record successful request metrics
            self._record_request_metric(
                request.method,
                request.url.path,
                response.status_code,
                time.time() - start_time,
                "success"
            )
            
            return response
            
        except HTTPException as e:
            # Handle known HTTP exceptions
            duration = time.time() - start_time
            
            # Log warning for client errors (4xx), error for server errors (5xx)
            log_level = logging.WARNING if 400 <= e.status_code < 500 else logging.ERROR
            
            if self.log_all_errors or e.status_code >= 500:
                logger.log(
                    log_level,
                    "HTTP exception occurred",
                    extra={
                        "request_id": request_id,
                        "status_code": e.status_code,
                        "detail": str(e.detail),
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": round(duration * 1000, 2),
                        "client_ip": self._get_client_ip(request)
                    }
                )
            
            # Record error metrics
            self._record_request_metric(
                request.method,
                request.url.path,
                e.status_code,
                duration,
                "http_exception"
            )
            
            # Format error response
            if isinstance(e.detail, dict):
                # Detail is already formatted (probably from our error functions)
                error_detail = e.detail
            else:
                # Format simple string detail
                error_detail = self._create_error_response(
                    error_code="HTTP_ERROR",
                    error_category=ErrorCategory.CLIENT_ERROR if 400 <= e.status_code < 500 else ErrorCategory.SERVER_ERROR,
                    message=str(e.detail),
                    request_id=request_id,
                    severity=ErrorSeverity.INFO if 400 <= e.status_code < 500 else ErrorSeverity.WARNING,
                    status_code=e.status_code
                )
            
            return JSONResponse(
                status_code=e.status_code,
                content=error_detail
            )
            
        except ValidationError as e:
            # Handle Pydantic validation errors
            duration = time.time() - start_time
            
            if self.log_all_errors:
                logger.warning(
                    "Validation error occurred",
                    extra={
                        "request_id": request_id,
                        "validation_errors": e.errors(),
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": round(duration * 1000, 2),
                        "client_ip": self._get_client_ip(request)
                    }
                )
            
            # Record error metrics
            self._record_request_metric(
                request.method,
                request.url.path,
                422,
                duration,
                "validation_error"
            )
            
            # Format validation errors
            field_errors = []
            for error in e.errors():
                field_errors.append({
                    "field": ".".join(str(loc) for loc in error["loc"]),
                    "message": error["msg"],
                    "type": error["type"],
                    "input": error.get("input")
                })
            
            error_response = self._create_validation_error_response(
                field_errors=field_errors,
                request_id=request_id
            )
            
            return JSONResponse(
                status_code=422,
                content=error_response
            )
            
        except Exception as e:
            # Handle all other unhandled exceptions
            duration = time.time() - start_time
            
            # Log critical error with full traceback
            logger.error(
                "Unhandled exception occurred",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration * 1000, 2),
                    "client_ip": self._get_client_ip(request),
                    "traceback": traceback.format_exc() if self.include_debug_info else None
                },
                exc_info=True
            )
            
            # Record error metrics
            self._record_request_metric(
                request.method,
                request.url.path,
                500,
                duration,
                "unhandled_exception"
            )
            
            # Track error frequency
            error_key = f"{type(e).__name__}:{request.url.path}"
            self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
            
            # Create error response
            error_response = self._create_error_response(
                error_code="INTERNAL_SERVER_ERROR",
                error_category=ErrorCategory.SERVER_ERROR,
                message="An unexpected error occurred while processing your request",
                request_id=request_id,
                severity=ErrorSeverity.CRITICAL,
                status_code=500,
                debug_info={
                    "error_type": type(e).__name__,
                    "error_count": self.error_counts[error_key]
                } if self.include_debug_info else None
            )
            
            return JSONResponse(
                status_code=500,
                content=error_response
            )
    
    def _create_error_response(
        self,
        error_code: str,
        error_category: ErrorCategory,
        message: str,
        request_id: str,
        severity: ErrorSeverity,
        status_code: int,
        details: Optional[Dict[str, Any]] = None,
        remediation_hint: Optional[str] = None,
        debug_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create standardized error response"""
        
        response = {
            "error_code": error_code,
            "error_category": error_category.value,
            "message": message,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            "severity": severity.value,
            "status_code": status_code
        }
        
        if details:
            response["details"] = details
        
        if remediation_hint:
            response["remediation_hint"] = remediation_hint
        
        if debug_info and self.include_debug_info:
            response["debug_info"] = debug_info
        
        # Add environment-specific fields
        if self.include_debug_info:
            response["environment"] = self.environment
            response["api_version"] = self.config_loader.get_section("application.version", "unknown")
        
        return response
    
    def _create_validation_error_response(
        self,
        field_errors: list,
        request_id: str
    ) -> Dict[str, Any]:
        """Create validation error response"""
        
        return self._create_error_response(
            error_code="VALIDATION_ERROR",
            error_category=ErrorCategory.CLIENT_ERROR,
            message="Request validation failed",
            request_id=request_id,
            severity=ErrorSeverity.INFO,
            status_code=422,
            details={
                "field_errors": field_errors,
                "error_count": len(field_errors)
            },
            remediation_hint="Check the request format and ensure all required fields are provided correctly"
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        # Check forwarded headers first
        forwarded_headers = ["X-Forwarded-For", "X-Real-IP", "CF-Connecting-IP"]
        
        for header in forwarded_headers:
            ip = request.headers.get(header)
            if ip:
                # Take first IP from comma-separated list
                return ip.split(",")[0].strip()
        
        # Fall back to direct connection
        if request.client and request.client.host:
            return request.client.host
        
        return "unknown"
    
    def _record_request_metric(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        error_type: str
    ):
        """Record request metrics (placeholder for metrics service integration)"""
        # This would integrate with the metrics service if available
        # For now, just log the metric
        try:
            from ..main import app_state
            metrics_service = app_state.get("metrics_service")
            
            if metrics_service:
                # Record request counter
                metrics_service.increment(
                    "sizecomparator_requests_total",
                    tags={
                        "method": method,
                        "endpoint": path,
                        "status": str(status_code),
                        "error_type": error_type
                    }
                )
                
                # Record request duration
                metrics_service.histogram(
                    "sizecomparator_request_duration_seconds",
                    duration,
                    tags={"endpoint": path}
                )
                
                # Record error rate
                if status_code >= 400:
                    metrics_service.increment(
                        "sizecomparator_errors_total",
                        tags={
                            "status_code": str(status_code),
                            "error_type": error_type,
                            "endpoint": path
                        }
                    )
        except Exception as e:
            # Don't let metrics recording break error handling
            logger.debug(f"Failed to record metrics: {e}")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        return {
            "total_error_types": len(self.error_counts),
            "error_counts": dict(self.error_counts),
            "most_frequent_errors": sorted(
                self.error_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }


# Custom exception classes for specific error scenarios
class WeightProcessingError(Exception):
    """Raised when weight processing fails"""
    
    def __init__(self, message: str, input_value: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.input_value = input_value
        self.details = details or {}


class AIProviderError(Exception):
    """Raised when AI provider operations fail"""
    
    def __init__(self, message: str, provider: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.provider = provider
        self.details = details or {}


class CacheError(Exception):
    """Raised when cache operations fail"""
    
    def __init__(self, message: str, operation: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.operation = operation
        self.details = details or {}


class RateLimitError(Exception):
    """Raised when rate limits are exceeded"""
    
    def __init__(self, message: str, limit: int = None, window: int = None):
        super().__init__(message)
        self.limit = limit
        self.window = window


# Helper functions for creating specific error responses
def create_weight_parsing_error(input_value: str, request_id: str) -> Dict[str, Any]:
    """Create standard weight parsing error response"""
    return {
        "error_code": "WEIGHT_PARSING_ERROR",
        "error_category": ErrorCategory.BUSINESS_LOGIC_ERROR.value,
        "message": f"Unable to parse weight format: {input_value}",
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat(),
        "severity": ErrorSeverity.INFO.value,
        "details": {
            "input": input_value,
            "expected_format": "number + unit (e.g., '5 kg')"
        },
        "remediation_hint": "Provide weight in format like '5 kg' or '2.5 pounds'"
    }


def create_ai_provider_error(provider: str, error_message: str, request_id: str) -> Dict[str, Any]:
    """Create standard AI provider error response"""
    return {
        "error_code": "AI_PROVIDER_ERROR",
        "error_category": ErrorCategory.INTEGRATION_ERROR.value,
        "message": "AI service temporarily unavailable",
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat(),
        "severity": ErrorSeverity.WARNING.value,
        "details": {
            "provider": provider,
            "error": error_message
        },
        "remediation_hint": "Please try again. The service will automatically retry with backup providers."
    }