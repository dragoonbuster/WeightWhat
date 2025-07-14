"""
Request ID Middleware for Distributed Tracing

This middleware handles request ID generation and propagation for ERROR_MONITORING_SPEC compliance:
- Extracts or generates unique request IDs
- Sets request context for logging
- Adds request ID to response headers
- Tracks request processing time
"""

import time
import uuid
from contextvars import ContextVar
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Context variable for request ID (thread-safe)
request_id_context: ContextVar[str] = ContextVar('request_id', default='')
request_start_time_context: ContextVar[float] = ContextVar('request_start_time', default=0.0)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Request ID middleware for distributed tracing and correlation.
    
    This middleware:
    1. Extracts request ID from headers (X-Request-ID, X-Correlation-ID, etc.)
    2. Generates new request ID if none provided
    3. Sets request context variables for logging
    4. Adds request ID and timing headers to responses
    5. Tracks request processing time
    """
    
    def __init__(
        self,
        app,
        request_id_header: str = "X-Request-ID",
        correlation_headers: list[str] = None,
        generate_if_missing: bool = True,
        include_processing_time: bool = True
    ):
        super().__init__(app)
        self.request_id_header = request_id_header
        self.correlation_headers = correlation_headers or [
            "X-Request-ID",
            "X-Correlation-ID", 
            "X-Trace-ID",
            "Request-ID"
        ]
        self.generate_if_missing = generate_if_missing
        self.include_processing_time = include_processing_time
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add request ID context"""
        
        # Record start time
        start_time = time.time()
        request_start_time_context.set(start_time)
        
        # Extract or generate request ID
        request_id = self._extract_request_id(request)
        if not request_id and self.generate_if_missing:
            request_id = self._generate_request_id()
        
        # Set request context
        if request_id:
            request_id_context.set(request_id)
            request.state.request_id = request_id
        
        # Add request metadata to state
        request.state.start_time = start_time
        request.state.method = request.method
        request.state.path = request.url.path
        request.state.client_ip = self._get_client_ip(request)
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Even if request fails, we want to add headers for debugging
            from fastapi.responses import JSONResponse
            processing_time = time.time() - start_time
            
            error_response = JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "request_id": request_id,
                    "processing_time_ms": round(processing_time * 1000, 2)
                }
            )
            
            if request_id:
                error_response.headers[self.request_id_header] = request_id
            if self.include_processing_time:
                error_response.headers["X-Processing-Time"] = f"{processing_time:.3f}"
            
            raise e
        
        # Add headers to response
        processing_time = time.time() - start_time
        
        if request_id:
            response.headers[self.request_id_header] = request_id
        
        if self.include_processing_time:
            response.headers["X-Processing-Time"] = f"{processing_time:.3f}"
            response.headers["X-Processing-Time-Ms"] = str(round(processing_time * 1000, 2))
        
        # Add CORS-safe headers
        response.headers["X-Response-Timestamp"] = str(int(time.time()))
        
        return response
    
    def _extract_request_id(self, request: Request) -> str:
        """Extract request ID from headers"""
        
        # Try each correlation header in order
        for header_name in self.correlation_headers:
            request_id = request.headers.get(header_name)
            if request_id:
                # Validate request ID format
                if self._is_valid_request_id(request_id):
                    return request_id
        
        return ""
    
    def _generate_request_id(self) -> str:
        """Generate new request ID"""
        return f"req_{uuid.uuid4().hex[:16]}"
    
    def _is_valid_request_id(self, request_id: str) -> bool:
        """Validate request ID format"""
        if not request_id or len(request_id) > 128:
            return False
        
        # Allow alphanumeric, hyphens, underscores
        import re
        return bool(re.match(r'^[a-zA-Z0-9\-_]+$', request_id))
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address with proxy support"""
        
        # Check for forwarded headers (common in load balancers)
        forwarded_headers = [
            "X-Forwarded-For",
            "X-Real-IP", 
            "CF-Connecting-IP",  # Cloudflare
            "X-Client-IP"
        ]
        
        for header in forwarded_headers:
            ip = request.headers.get(header)
            if ip:
                # X-Forwarded-For can contain multiple IPs (client, proxy1, proxy2)
                # Take the first one (original client)
                if "," in ip:
                    ip = ip.split(",")[0].strip()
                
                if self._is_valid_ip(ip):
                    return ip
        
        # Fall back to direct connection
        if request.client and request.client.host:
            return request.client.host
        
        return "unknown"
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Basic IP address validation"""
        try:
            import ipaddress
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False


def get_current_request_id() -> str:
    """Get current request ID from context"""
    try:
        return request_id_context.get()
    except LookupError:
        return ""


def get_request_start_time() -> float:
    """Get current request start time from context"""
    try:
        return request_start_time_context.get()
    except LookupError:
        return 0.0


def get_request_processing_time() -> float:
    """Get current request processing time"""
    start_time = get_request_start_time()
    if start_time > 0:
        return time.time() - start_time
    return 0.0


# Utility functions for logging integration
def get_request_context() -> dict:
    """Get request context for structured logging"""
    request_id = get_current_request_id()
    processing_time = get_request_processing_time()
    
    context = {}
    if request_id:
        context["request_id"] = request_id
    if processing_time > 0:
        context["processing_time_ms"] = round(processing_time * 1000, 2)
    
    return context


def add_request_context_to_log_record(record):
    """Add request context to log record (for custom log formatters)"""
    context = get_request_context()
    for key, value in context.items():
        setattr(record, key, value)
    return record


# Example usage with structlog or standard logging
def configure_request_logging():
    """Configure logging to include request context"""
    import logging
    
    # Add request context to all log records
    class RequestContextFilter(logging.Filter):
        def filter(self, record):
            context = get_request_context()
            for key, value in context.items():
                setattr(record, key, value)
            return True
    
    # Add filter to root logger
    root_logger = logging.getLogger()
    root_logger.addFilter(RequestContextFilter())