"""
Request tracing and correlation ID management for SizeComparator.

Implements BACKEND_CORE_SPEC request_id_context propagation and provides
middleware for FastAPI integration with comprehensive request tracking.
"""

import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Callable, Awaitable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import HTTPException
import asyncio

from .monitoring import get_logger, get_metrics, get_performance_monitor
from .exceptions import map_exception_to_error_response, ErrorHandler


# Context variables for request tracing
request_id_context: ContextVar[str] = ContextVar('request_id', default='')
user_id_context: ContextVar[str] = ContextVar('user_id', default='')
session_id_context: ContextVar[str] = ContextVar('session_id', default='')
operation_context: ContextVar[str] = ContextVar('operation', default='')


class RequestTrace:
    """Request trace data structure for tracking request lifecycle."""
    
    def __init__(
        self,
        request_id: str,
        method: str,
        path: str,
        query_params: Dict[str, str],
        headers: Dict[str, str],
        client_ip: str,
        user_agent: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        self.request_id = request_id
        self.method = method
        self.path = path
        self.query_params = query_params
        self.headers = headers
        self.client_ip = client_ip
        self.user_agent = user_agent
        self.user_id = user_id
        self.session_id = session_id
        
        # Timing information
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.duration: Optional[float] = None
        
        # Response information
        self.status_code: Optional[int] = None
        self.response_size: Optional[int] = None
        self.error_info: Optional[Dict[str, Any]] = None
        
        # Context information
        self.context_data: Dict[str, Any] = {}
        
        # Span tracking for distributed tracing
        self.spans: Dict[str, Dict[str, Any]] = {}
        self.current_span: Optional[str] = None
    
    def finish(self, status_code: int, response_size: Optional[int] = None):
        """Mark request as finished and calculate duration."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.status_code = status_code
        self.response_size = response_size
    
    def add_context(self, **kwargs):
        """Add context data to the trace."""
        self.context_data.update(kwargs)
    
    def start_span(self, name: str, **attributes) -> str:
        """Start a new span for operation tracking."""
        span_id = str(uuid.uuid4())
        self.spans[span_id] = {
            'name': name,
            'start_time': time.time(),
            'end_time': None,
            'duration': None,
            'attributes': attributes,
            'parent_span': self.current_span
        }
        self.current_span = span_id
        return span_id
    
    def finish_span(self, span_id: str, **attributes):
        """Finish a span and calculate duration."""
        if span_id in self.spans:
            span = self.spans[span_id]
            span['end_time'] = time.time()
            span['duration'] = span['end_time'] - span['start_time']
            span['attributes'].update(attributes)
            
            # Set parent as current span
            self.current_span = span.get('parent_span')
    
    def add_error(self, error: Exception):
        """Add error information to the trace."""
        self.error_info = {
            'type': error.__class__.__name__,
            'message': str(error),
            'timestamp': time.time()
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary for logging."""
        return {
            'request_id': self.request_id,
            'method': self.method,
            'path': self.path,
            'query_params': self.query_params,
            'client_ip': self.client_ip,
            'user_agent': self.user_agent,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'status_code': self.status_code,
            'response_size': self.response_size,
            'error_info': self.error_info,
            'context_data': self.context_data,
            'spans': self.spans
        }


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for request tracing and monitoring.
    
    Implements BACKEND_CORE_SPEC request ID propagation and integrates
    with ERROR_MONITORING_SPEC for comprehensive request tracking.
    """
    
    def __init__(
        self,
        app,
        service_name: str = "sizecomparator",
        include_headers: bool = False,
        include_query_params: bool = True,
        sensitive_headers: Optional[list] = None
    ):
        super().__init__(app)
        self.service_name = service_name
        self.include_headers = include_headers
        self.include_query_params = include_query_params
        self.sensitive_headers = sensitive_headers or [
            'authorization', 'x-api-key', 'cookie', 'x-auth-token'
        ]
        
        # Get monitoring components
        self.logger = get_logger()
        self.metrics = get_metrics()
        self.performance_monitor = get_performance_monitor()
        self.error_handler = ErrorHandler(self.metrics, self.logger)
    
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """Process request with tracing and monitoring."""
        
        # Generate or extract request ID
        request_id = self._get_request_id(request)
        
        # Set context variables
        request_id_context.set(request_id)
        user_id_context.set(self._get_user_id(request))
        session_id_context.set(self._get_session_id(request))
        operation_context.set(f"{request.method} {request.url.path}")
        
        # Create request trace
        trace = self._create_request_trace(request, request_id)
        
        # Start request span
        request_span_id = trace.start_span(
            f"{request.method} {request.url.path}",
            method=request.method,
            path=request.url.path,
            client_ip=trace.client_ip
        )
        
        # Log request start
        self.logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=trace.client_ip,
            user_agent=trace.user_agent
        )
        
        start_time = time.time()
        response = None
        error_occurred = False
        
        try:
            # Store trace in request state for access in endpoints
            request.state.trace = trace
            
            # Process request
            response = await call_next(request)
            
            # Finish request span
            trace.finish_span(
                request_span_id,
                status_code=response.status_code,
                response_size=len(response.body) if hasattr(response, 'body') else None
            )
            
            # Finish trace
            response_size = self._get_response_size(response)
            trace.finish(response.status_code, response_size)
            
            return response
            
        except Exception as exc:
            error_occurred = True
            duration = time.time() - start_time
            
            # Add error to trace
            trace.add_error(exc)
            
            # Finish request span with error
            trace.finish_span(
                request_span_id,
                error=True,
                error_type=exc.__class__.__name__,
                error_message=str(exc)
            )
            
            # Handle exception
            if isinstance(exc, HTTPException):
                # FastAPI HTTP exceptions
                trace.finish(exc.status_code)
                response = Response(
                    content=exc.detail,
                    status_code=exc.status_code,
                    headers=getattr(exc, 'headers', None)
                )
            else:
                # Other exceptions - convert to error response
                error_response = self.error_handler.handle_exception(
                    exc, 
                    endpoint=request.url.path,
                    request_id=request_id
                )
                
                trace.finish(error_response.get_http_status_code())
                
                # Create JSON response
                response = Response(
                    content=error_response.model_dump_json(),
                    status_code=error_response.get_http_status_code(),
                    media_type="application/json"
                )
            
            return response
            
        finally:
            # Always perform cleanup and logging
            duration = time.time() - start_time
            
            # Record performance metrics
            self.performance_monitor.record_request_performance(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code if response else 500,
                duration=duration,
                error_category=trace.error_info.get('type') if trace.error_info else None,
                error_code=trace.error_info.get('message') if trace.error_info else None
            )
            
            # Record metrics
            self.metrics.record_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code if response else 500,
                duration=duration
            )
            
            # Add response headers
            if response:
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Response-Time"] = f"{duration:.3f}s"
            
            # Log request completion
            log_level = "error" if error_occurred else "info"
            log_message = "Request failed" if error_occurred else "Request completed"
            
            log_context = {
                'request_id': request_id,
                'method': request.method,
                'path': request.url.path,
                'status_code': response.status_code if response else 500,
                'duration_seconds': duration,
                'response_size': trace.response_size,
                'spans_count': len(trace.spans)
            }
            
            if trace.error_info:
                log_context['error_type'] = trace.error_info['type']
                log_context['error_message'] = trace.error_info['message']
            
            getattr(self.logger, log_level)(log_message, **log_context)
            
            # Log detailed trace for debugging (debug level)
            self.logger.debug(
                "Request trace details",
                trace=trace.to_dict()
            )
    
    def _get_request_id(self, request: Request) -> str:
        """Extract or generate request ID."""
        # Check headers for existing request ID
        request_id = (
            request.headers.get('X-Request-ID') or
            request.headers.get('X-Correlation-ID') or
            request.headers.get('X-Trace-ID')
        )
        
        if not request_id:
            request_id = str(uuid.uuid4())
        
        return request_id
    
    def _get_user_id(self, request: Request) -> str:
        """Extract user ID from request."""
        # Try various common headers and auth patterns
        user_id = (
            request.headers.get('X-User-ID') or
            request.headers.get('X-User') or
            ''
        )
        
        # Could also extract from JWT token, session, etc.
        return user_id
    
    def _get_session_id(self, request: Request) -> str:
        """Extract session ID from request."""
        session_id = (
            request.headers.get('X-Session-ID') or
            request.headers.get('X-Session') or
            ''
        )
        
        # Could also extract from cookies
        return session_id
    
    def _create_request_trace(self, request: Request, request_id: str) -> RequestTrace:
        """Create request trace object."""
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Get headers (sanitized)
        headers = self._sanitize_headers(dict(request.headers)) if self.include_headers else {}
        
        # Get query parameters
        query_params = dict(request.query_params) if self.include_query_params else {}
        
        # Get user agent
        user_agent = request.headers.get('user-agent', '')
        
        return RequestTrace(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query_params=query_params,
            headers=headers,
            client_ip=client_ip,
            user_agent=user_agent,
            user_id=user_id_context.get(),
            session_id=session_id_context.get()
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check for forwarded headers
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fallback to direct client
        client_host = getattr(request.client, 'host', 'unknown')
        return client_host
    
    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Remove sensitive headers from logging."""
        sanitized = {}
        
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value
        
        return sanitized
    
    def _get_response_size(self, response: Response) -> Optional[int]:
        """Get response size in bytes."""
        try:
            if hasattr(response, 'body'):
                return len(response.body)
            
            content_length = response.headers.get('content-length')
            if content_length:
                return int(content_length)
            
            return None
        except:
            return None


class TracingContext:
    """Context manager for manual span tracking within request processing."""
    
    def __init__(
        self,
        name: str,
        trace: Optional[RequestTrace] = None,
        **attributes
    ):
        self.name = name
        self.trace = trace
        self.attributes = attributes
        self.span_id: Optional[str] = None
        self.logger = get_logger()
    
    def __enter__(self):
        """Start span."""
        if self.trace:
            self.span_id = self.trace.start_span(self.name, **self.attributes)
            
            self.logger.debug(
                f"Started span: {self.name}",
                span_id=self.span_id,
                span_name=self.name,
                **self.attributes
            )
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Finish span."""
        if self.trace and self.span_id:
            # Add error information if exception occurred
            if exc_type:
                self.attributes.update({
                    'error': True,
                    'error_type': exc_type.__name__,
                    'error_message': str(exc_val)
                })
            
            self.trace.finish_span(self.span_id, **self.attributes)
            
            self.logger.debug(
                f"Finished span: {self.name}",
                span_id=self.span_id,
                span_name=self.name,
                error_occurred=exc_type is not None,
                **self.attributes
            )
    
    def add_attribute(self, key: str, value: Any):
        """Add attribute to span."""
        self.attributes[key] = value
        if self.trace and self.span_id and self.span_id in self.trace.spans:
            self.trace.spans[self.span_id]['attributes'][key] = value


# Utility functions for tracing
def get_current_request_id() -> str:
    """Get current request ID from context."""
    return request_id_context.get()


def get_current_user_id() -> str:
    """Get current user ID from context."""
    return user_id_context.get()


def get_current_session_id() -> str:
    """Get current session ID from context."""
    return session_id_context.get()


def get_current_operation() -> str:
    """Get current operation from context."""
    return operation_context.get()


def get_request_trace(request: Request) -> Optional[RequestTrace]:
    """Get request trace from FastAPI request state."""
    return getattr(request.state, 'trace', None)


def create_span(
    name: str,
    request: Optional[Request] = None,
    **attributes
) -> TracingContext:
    """Create a new tracing span context manager."""
    trace = get_request_trace(request) if request else None
    return TracingContext(name, trace, **attributes)


# Decorator for automatic span creation
def trace_operation(name: Optional[str] = None, **span_attributes):
    """Decorator to automatically trace function execution."""
    
    def decorator(func):
        operation_name = name or f"{func.__module__}.{func.__name__}"
        
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                # Try to get trace from kwargs if Request is passed
                trace = None
                for arg in args:
                    if hasattr(arg, 'state') and hasattr(arg.state, 'trace'):
                        trace = arg.state.trace
                        break
                
                with TracingContext(operation_name, trace, **span_attributes) as span:
                    try:
                        result = await func(*args, **kwargs)
                        span.add_attribute('success', True)
                        return result
                    except Exception as e:
                        span.add_attribute('success', False)
                        span.add_attribute('error_details', str(e))
                        raise
            
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                # Try to get trace from kwargs if Request is passed
                trace = None
                for arg in args:
                    if hasattr(arg, 'state') and hasattr(arg.state, 'trace'):
                        trace = arg.state.trace
                        break
                
                with TracingContext(operation_name, trace, **span_attributes) as span:
                    try:
                        result = func(*args, **kwargs)
                        span.add_attribute('success', True)
                        return result
                    except Exception as e:
                        span.add_attribute('success', False)
                        span.add_attribute('error_details', str(e))
                        raise
            
            return sync_wrapper
    
    return decorator


class DistributedTracingHeaders:
    """Helper class for distributed tracing header management."""
    
    # Standard tracing headers
    TRACE_ID = "X-Trace-ID"
    SPAN_ID = "X-Span-ID"
    PARENT_SPAN_ID = "X-Parent-Span-ID"
    REQUEST_ID = "X-Request-ID"
    CORRELATION_ID = "X-Correlation-ID"
    
    @classmethod
    def extract_trace_context(cls, headers: Dict[str, str]) -> Dict[str, str]:
        """Extract tracing context from headers."""
        return {
            'trace_id': headers.get(cls.TRACE_ID, ''),
            'span_id': headers.get(cls.SPAN_ID, ''),
            'parent_span_id': headers.get(cls.PARENT_SPAN_ID, ''),
            'request_id': headers.get(cls.REQUEST_ID, ''),
            'correlation_id': headers.get(cls.CORRELATION_ID, '')
        }
    
    @classmethod
    def inject_trace_context(
        cls, 
        headers: Dict[str, str],
        trace_id: str,
        span_id: str,
        parent_span_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, str]:
        """Inject tracing context into headers."""
        headers[cls.TRACE_ID] = trace_id
        headers[cls.SPAN_ID] = span_id
        
        if parent_span_id:
            headers[cls.PARENT_SPAN_ID] = parent_span_id
        
        if request_id:
            headers[cls.REQUEST_ID] = request_id
            headers[cls.CORRELATION_ID] = request_id
        
        return headers