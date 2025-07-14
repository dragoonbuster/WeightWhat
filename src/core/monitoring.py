"""
Error Monitoring and Observability System for SizeComparator

This module implements comprehensive error handling, structured logging, metrics collection,
and circuit breaker patterns as specified in ERROR_MONITORING_SPEC.md.

Integrates with:
- DATA_MODELS error response models
- CONFIG_LOADER for monitoring configuration
- ENV_MANAGER for monitoring environment variables
"""

import json
import logging
import time
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Dict, Any, Optional, List, Set, Callable, Union
from uuid import uuid4
import re

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, CONTENT_TYPE_LATEST, generate_latest
from pythonjsonlogger import jsonlogger

from ..models.errors import ErrorCategory, ErrorSeverity, BaseErrorResponse


class LogLevel(str, Enum):
    """Log levels aligned with CONFIG_SYSTEM_SPEC"""
    DEBUG = "DEBUG"
    INFO = "INFO" 
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


class CircuitBreakerState(str, Enum):
    """Circuit breaker states aligned with AI_PROVIDER_SPEC"""
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class ServiceName(str, Enum):
    """Service names for distributed tracing"""
    API_GATEWAY = "api_gateway"
    WEIGHT_PROCESSOR = "weight_processor"
    AI_PROVIDER = "ai_provider"
    CACHE_SERVICE = "cache_service"
    CONFIG_LOADER = "config_loader"


class RequestContext:
    """Thread-local request context for distributed tracing"""
    
    def __init__(self):
        self._local = threading.local()
    
    def set_request_id(self, request_id: str):
        """Set request ID for current thread"""
        self._local.request_id = request_id
    
    def get_request_id(self) -> str:
        """Get request ID for current thread, generate if missing"""
        if not hasattr(self._local, 'request_id'):
            self._local.request_id = str(uuid4())
        return self._local.request_id
    
    def set_context(self, **kwargs):
        """Set additional context for current thread"""
        if not hasattr(self._local, 'context'):
            self._local.context = {}
        self._local.context.update(kwargs)
    
    def get_context(self) -> Dict[str, Any]:
        """Get context for current thread"""
        return getattr(self._local, 'context', {})
    
    def clear(self):
        """Clear context for current thread"""
        self._local.__dict__.clear()


# Global request context
request_context = RequestContext()


class PIISanitizer:
    """Sanitizes logs to prevent PII exposure"""
    
    # Patterns to detect and mask sensitive data
    PII_PATTERNS = [
        (re.compile(r'SIZECOMPARATOR_[A-Z_]*API_KEY', re.IGNORECASE), '[API_KEY_MASKED]'),
        (re.compile(r'Bearer\s+[A-Za-z0-9\-_=]+', re.IGNORECASE), 'Bearer [TOKEN_MASKED]'),
        (re.compile(r'sk-[A-Za-z0-9]{48}', re.IGNORECASE), '[OPENAI_KEY_MASKED]'),
        (re.compile(r'claude-[A-Za-z0-9\-_]{40,}', re.IGNORECASE), '[ANTHROPIC_KEY_MASKED]'),
        (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL_MASKED]'),
        (re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'), '[CARD_MASKED]'),
    ]
    
    @classmethod
    def sanitize(cls, data: Any) -> Any:
        """Sanitize data to remove PII"""
        if isinstance(data, str):
            return cls._sanitize_string(data)
        elif isinstance(data, dict):
            return {k: cls.sanitize(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls.sanitize(item) for item in data]
        else:
            return data
    
    @classmethod
    def _sanitize_string(cls, text: str) -> str:
        """Sanitize string content"""
        for pattern, replacement in cls.PII_PATTERNS:
            text = pattern.sub(replacement, text)
        return text


class StructuredLogger:
    """Structured logging with request ID propagation and PII protection"""
    
    def __init__(self, service_name: ServiceName, environment: str = "development"):
        self.service_name = service_name
        self.environment = environment
        self.logger = logging.getLogger(f"sizecomparator.{service_name}")
        
        # Configure JSON formatter
        formatter = jsonlogger.JsonFormatter(
            '%(timestamp)s %(request_id)s %(service_name)s %(environment)s %(levelname)s %(message)s'
        )
        
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        
        self.logger.handlers.clear()
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def _create_log_record(self, level: str, message: str, **context) -> Dict[str, Any]:
        """Create standardized log record"""
        record = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'request_id': request_context.get_request_id(),
            'service_name': self.service_name,
            'environment': self.environment,
            'level': level,
            'message': message,
        }
        
        # Add request context
        record.update(request_context.get_context())
        
        # Add additional context
        record.update(context)
        
        # Sanitize PII
        return PIISanitizer.sanitize(record)
    
    def debug(self, message: str, **context):
        """Log debug message"""
        record = self._create_log_record("DEBUG", message, **context)
        self.logger.debug(json.dumps(record))
    
    def info(self, message: str, **context):
        """Log info message"""
        record = self._create_log_record("INFO", message, **context)
        self.logger.info(json.dumps(record))
    
    def warn(self, message: str, **context):
        """Log warning message"""
        record = self._create_log_record("WARN", message, **context)
        self.logger.warning(json.dumps(record))
    
    def error(self, message: str, **context):
        """Log error message"""
        record = self._create_log_record("ERROR", message, **context)
        self.logger.error(json.dumps(record))
    
    def fatal(self, message: str, **context):
        """Log fatal message"""
        record = self._create_log_record("FATAL", message, **context)
        self.logger.critical(json.dumps(record))


class MetricsCollector:
    """Prometheus metrics collection for monitoring"""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        
        # Request metrics (RED metrics)
        self.request_counter = Counter(
            'sizecomparator_requests_total',
            'Total number of requests',
            ['service', 'endpoint', 'method', 'status'],
            registry=self.registry
        )
        
        self.request_duration = Histogram(
            'sizecomparator_request_duration_seconds',
            'Request duration in seconds',
            ['service', 'endpoint', 'method'],
            registry=self.registry
        )
        
        self.error_counter = Counter(
            'sizecomparator_errors_total',
            'Total number of errors',
            ['service', 'error_category', 'error_code'],
            registry=self.registry
        )
        
        # AI Provider metrics
        self.ai_provider_requests = Counter(
            'sizecomparator_ai_provider_requests_total',
            'AI provider requests',
            ['provider', 'status'],
            registry=self.registry
        )
        
        self.ai_provider_duration = Histogram(
            'sizecomparator_ai_provider_duration_seconds',
            'AI provider response time',
            ['provider'],
            registry=self.registry
        )
        
        # Circuit breaker metrics
        self.circuit_breaker_state = Gauge(
            'sizecomparator_circuit_breaker_state',
            'Circuit breaker state (0=CLOSED, 1=OPEN, 2=HALF_OPEN)',
            ['service', 'provider'],
            registry=self.registry
        )
        
        # Cache metrics
        self.cache_operations = Counter(
            'sizecomparator_cache_operations_total',
            'Cache operations',
            ['operation', 'result'],
            registry=self.registry
        )
        
        # Business metrics
        self.weight_comparisons = Counter(
            'sizecomparator_weight_comparisons_total',
            'Weight comparisons processed',
            ['unit_from', 'unit_to'],
            registry=self.registry
        )
        
        # Resource metrics
        self.active_requests = Gauge(
            'sizecomparator_active_requests',
            'Number of active requests',
            ['service'],
            registry=self.registry
        )
    
    def record_request(self, service: str, endpoint: str, method: str, status: int, duration: float):
        """Record request metrics"""
        self.request_counter.labels(service=service, endpoint=endpoint, method=method, status=status).inc()
        self.request_duration.labels(service=service, endpoint=endpoint, method=method).observe(duration)
    
    def record_error(self, service: str, error_category: str, error_code: str):
        """Record error metrics"""
        self.error_counter.labels(service=service, error_category=error_category, error_code=error_code).inc()
    
    def record_ai_provider_request(self, provider: str, status: str, duration: float):
        """Record AI provider metrics"""
        self.ai_provider_requests.labels(provider=provider, status=status).inc()
        self.ai_provider_duration.labels(provider=provider).observe(duration)
    
    def set_circuit_breaker_state(self, service: str, provider: str, state: CircuitBreakerState):
        """Set circuit breaker state"""
        state_value = {"CLOSED": 0, "OPEN": 1, "HALF_OPEN": 2}[state]
        self.circuit_breaker_state.labels(service=service, provider=provider).set(state_value)
    
    def record_cache_operation(self, operation: str, result: str):
        """Record cache operation"""
        self.cache_operations.labels(operation=operation, result=result).inc()
    
    def record_weight_comparison(self, unit_from: str, unit_to: str):
        """Record weight comparison"""
        self.weight_comparisons.labels(unit_from=unit_from, unit_to=unit_to).inc()
    
    def set_active_requests(self, service: str, count: int):
        """Set active request count"""
        self.active_requests.labels(service=service).set(count)
    
    def get_metrics(self) -> str:
        """Get Prometheus-formatted metrics"""
        return generate_latest(self.registry).decode('utf-8')
    
    def update_circuit_breaker_state(self, provider: str, state):
        """Update circuit breaker state for provider."""
        state_value = {
            "CLOSED": 0, 
            "OPEN": 1, 
            "HALF_OPEN": 2
        }.get(str(state).upper(), 0)
        self.circuit_breaker_state.labels(service="ai_provider", provider=provider).set(state_value)
    
    def record_provider_fallback(self, original_provider: str, fallback_provider: str, 
                                attempt_number: int, success: bool):
        """Record provider fallback metrics."""
        # Add fallback metrics if not already defined
        if not hasattr(self, 'provider_fallback_counter'):
            self.provider_fallback_counter = Counter(
                'sizecomparator_provider_fallback_total',
                'Provider fallback attempts',
                ['original_provider', 'fallback_provider', 'success'],
                registry=self.registry
            )
        
        self.provider_fallback_counter.labels(
            original_provider=original_provider,
            fallback_provider=fallback_provider,
            success=str(success).lower()
        ).inc()


class CircuitBreaker:
    """Circuit breaker implementation for service protection"""
    
    def __init__(self, 
                 name: str,
                 failure_threshold: int = 5,
                 success_threshold: int = 2,
                 timeout_seconds: int = 60,
                 metrics_collector: Optional[MetricsCollector] = None):
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds
        self.metrics_collector = metrics_collector
        
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self._lock = threading.Lock()
        
        self.logger = StructuredLogger(ServiceName.API_GATEWAY)
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator for circuit breaker protection"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)
        return wrapper
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        with self._lock:
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self._move_to_half_open()
                else:
                    self.logger.warn(f"Circuit breaker {self.name} is OPEN, rejecting request")
                    raise CircuitBreakerOpenError(f"Circuit breaker {self.name} is open")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset"""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.timeout_seconds
    
    def _move_to_half_open(self):
        """Move circuit breaker to half-open state"""
        self.state = CircuitBreakerState.HALF_OPEN
        self.success_count = 0
        self.logger.info(f"Circuit breaker {self.name} moved to HALF_OPEN")
        self._update_metrics()
    
    def _on_success(self):
        """Handle successful operation"""
        with self._lock:
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self._move_to_closed()
            elif self.state == CircuitBreakerState.CLOSED:
                self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed operation"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state in [CircuitBreakerState.CLOSED, CircuitBreakerState.HALF_OPEN]:
                if self.failure_count >= self.failure_threshold:
                    self._move_to_open()
    
    def _move_to_closed(self):
        """Move circuit breaker to closed state"""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.logger.info(f"Circuit breaker {self.name} moved to CLOSED")
        self._update_metrics()
    
    def _move_to_open(self):
        """Move circuit breaker to open state"""
        self.state = CircuitBreakerState.OPEN
        self.logger.error(f"Circuit breaker {self.name} moved to OPEN after {self.failure_count} failures")
        self._update_metrics()
    
    def _update_metrics(self):
        """Update circuit breaker metrics"""
        if self.metrics_collector:
            self.metrics_collector.set_circuit_breaker_state("circuit_breaker", self.name, self.state)


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class ErrorMonitor:
    """Central error monitoring and handling"""
    
    def __init__(self, metrics_collector: MetricsCollector, logger: StructuredLogger):
        self.metrics_collector = metrics_collector
        self.logger = logger
        self.error_counts: Dict[str, int] = {}
        self.rate_limits: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def handle_error(self, error: Exception, service: str, context: Optional[Dict[str, Any]] = None) -> BaseErrorResponse:
        """Handle and categorize errors"""
        error_category, error_code = self._categorize_error(error)
        
        # Record metrics
        self.metrics_collector.record_error(service, error_category.value, error_code)
        
        # Check rate limiting
        if self._should_rate_limit(error_code):
            self.logger.warn(f"Rate limiting error {error_code}", error_type=type(error).__name__)
            return BaseErrorResponse(
                error_code="RATE_LIMITED",
                error_category=ErrorCategory.SERVER_ERROR,
                message="Error rate limited to prevent log flooding",
                request_id=request_context.get_request_id(),
                timestamp=datetime.now(timezone.utc),
                severity=ErrorSeverity.MEDIUM
            )
        
        # Log error with context
        log_context = context or {}
        log_context.update({
            'error_type': type(error).__name__,
            'error_category': error_category.value,
            'error_code': error_code,
            'service': service
        })
        
        self.logger.error(f"Error in {service}: {str(error)}", **log_context)
        
        return BaseErrorResponse(
            error_code=error_code,
            error_category=error_category,
            message=str(error),
            request_id=request_context.get_request_id(),
            timestamp=datetime.now(timezone.utc),
            severity=self._determine_severity(error_category)
        )
    
    def _categorize_error(self, error: Exception) -> tuple[ErrorCategory, str]:
        """Categorize error and assign error code"""
        error_type = type(error).__name__
        
        # Client errors (4xx)
        if error_type in ['ValidationError', 'ValueError', 'KeyError']:
            return ErrorCategory.CLIENT_ERROR, f"CLIENT_{error_type.upper()}"
        
        # Integration errors (external services)
        elif error_type in ['ConnectionError', 'TimeoutError', 'HTTPError']:
            return ErrorCategory.INTEGRATION_ERROR, f"INTEGRATION_{error_type.upper()}"
        
        # Business logic errors
        elif error_type in ['WeightProcessingError', 'InvalidWeightError']:
            return ErrorCategory.BUSINESS_LOGIC_ERROR, f"BUSINESS_{error_type.upper()}"
        
        # Server errors (5xx) - default
        else:
            return ErrorCategory.SERVER_ERROR, f"SERVER_{error_type.upper()}"
    
    def _should_rate_limit(self, error_code: str) -> bool:
        """Check if error should be rate limited"""
        current_time = time.time()
        
        with self._lock:
            # Count errors in last minute
            if error_code not in self.error_counts:
                self.error_counts[error_code] = 0
                self.rate_limits[error_code] = current_time
            
            # Reset counter if minute passed
            if current_time - self.rate_limits[error_code] >= 60:
                self.error_counts[error_code] = 0
                self.rate_limits[error_code] = current_time
            
            self.error_counts[error_code] += 1
            
            # Rate limit after 10 errors per minute
            return self.error_counts[error_code] > 10
    
    def _determine_severity(self, category: ErrorCategory) -> ErrorSeverity:
        """Determine error severity based on category"""
        severity_map = {
            ErrorCategory.CLIENT_ERROR: ErrorSeverity.LOW,
            ErrorCategory.BUSINESS_LOGIC_ERROR: ErrorSeverity.MEDIUM,
            ErrorCategory.INTEGRATION_ERROR: ErrorSeverity.HIGH,
            ErrorCategory.SERVER_ERROR: ErrorSeverity.CRITICAL
        }
        return severity_map.get(category, ErrorSeverity.MEDIUM)


# Global monitoring instances
metrics_collector = MetricsCollector()
logger = StructuredLogger(ServiceName.API_GATEWAY)
error_monitor = ErrorMonitor(metrics_collector, logger)


@contextmanager
def request_tracking(request_id: Optional[str] = None, **context):
    """Context manager for request tracking"""
    if request_id is None:
        request_id = str(uuid4())
    
    request_context.set_request_id(request_id)
    request_context.set_context(**context)
    
    try:
        yield request_id
    finally:
        request_context.clear()


def monitor_performance(service: str, endpoint: str, method: str = "GET"):
    """Decorator for performance monitoring"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            status = 200
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = 500
                raise
            finally:
                duration = time.time() - start_time
                metrics_collector.record_request(service, endpoint, method, status, duration)
        
        return wrapper
    return decorator


def get_health_metrics() -> Dict[str, Any]:
    """Get system health metrics"""
    return {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'metrics_endpoint': '/metrics',
        'circuit_breakers': {
            # Will be populated by circuit breaker instances
        },
        'request_id': request_context.get_request_id()
    }


# Global instances
_logger = None
_metrics = None


def get_logger():
    """Get the global logger instance."""
    global _logger
    if _logger is None:
        _logger = logging.getLogger("sizecomparator")
        if not _logger.handlers:
            handler = logging.StreamHandler()
            formatter = jsonlogger.JsonFormatter()
            handler.setFormatter(formatter)
            _logger.addHandler(handler)
            _logger.setLevel(logging.INFO)
    return _logger


def get_metrics():
    """Get the global metrics collector instance."""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics