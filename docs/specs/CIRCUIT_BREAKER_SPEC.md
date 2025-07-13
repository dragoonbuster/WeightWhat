# Circuit Breaker Implementation Specification for SizeComparator

## Overview
This specification defines a comprehensive circuit breaker implementation for the SizeComparator system that provides robust protection for AI providers and external services. The circuit breaker serves as the central fault tolerance mechanism, integrating with ERROR_MONITORING_SPEC for observability and AI_PROVIDER_SPEC for provider protection while ensuring system resilience and graceful degradation under failure conditions.

## Context and Integration Requirements

### Integration with ERROR_MONITORING_SPEC
The circuit breaker must integrate seamlessly with the centralized monitoring system:
- **State Change Logging**: All circuit breaker state transitions (CLOSED→OPEN→HALF_OPEN) must emit structured log events with request IDs for correlation
- **Metrics Integration**: Circuit breaker metrics must feed into the Prometheus /metrics endpoint for monitoring dashboard integration
- **Alert Generation**: Circuit state changes must trigger appropriate alerts with severity levels aligned to monitoring thresholds
- **Request ID Propagation**: All circuit breaker events must include request IDs from BACKEND_CORE_SPEC request_id_context for end-to-end tracing

### Integration with AI_PROVIDER_SPEC  
Circuit breaker implementation must protect AI providers while maintaining service availability:
- **Provider Health Tracking**: Monitor AI provider response times, success rates, and timeout patterns
- **Graceful Degradation**: Implement fallback provider selection when primary providers are circuit broken
- **Rate Limit Protection**: Prevent cascading failures when providers hit rate limits
- **Provider-Specific Configuration**: Support different thresholds for OpenAI, Anthropic, and X.ai based on their characteristics

### Integration with DEPLOYMENT_OPS_SPEC
Circuit breaker health must be exposed through deployment health checks:
- **Health Endpoint Integration**: Circuit breaker states must be reported via /health and /ready endpoints
- **SLA Impact Reporting**: Circuit breaker state must feed into 99% uptime SLA calculations
- **Load Balancer Signals**: Provide signals for load balancer traffic routing decisions
- **Graceful Shutdown Support**: Handle circuit state during deployment operations

## 1. Circuit Breaker State Machine Implementation

### 1.1 Core State Definitions
Implement the three-state circuit breaker pattern with precise state management:

```python
from enum import Enum
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable, List
import asyncio
import uuid
from dataclasses import dataclass, field
import logging
from collections import defaultdict
import time

class CircuitState(Enum):
    """Circuit breaker states aligned with AI_PROVIDER_SPEC definitions."""
    CLOSED = "closed"      # Normal operation, requests allowed
    OPEN = "open"          # Failing state, requests rejected immediately  
    HALF_OPEN = "half_open"  # Testing recovery, limited requests allowed

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior with provider-specific tuning."""
    # Failure detection thresholds
    failure_threshold: int = 5           # Consecutive failures to open circuit
    success_threshold: int = 2           # Consecutive successes to close from half-open
    timeout_seconds: int = 60           # Time to wait before attempting recovery
    
    # Half-open state configuration  
    half_open_max_calls: int = 3        # Maximum concurrent calls in half-open
    half_open_success_ratio: float = 0.8  # Required success ratio in half-open
    
    # Time window configuration
    failure_time_window: int = 300      # Time window for failure counting (seconds)
    rolling_window_size: int = 50       # Size of rolling window for metrics
    
    # Provider-specific overrides
    timeout_multiplier: float = 1.0     # Multiply base timeout for specific providers
    custom_error_detector: Optional[Callable] = None  # Custom error classification
    
    # Monitoring integration
    enable_metrics: bool = True         # Emit Prometheus metrics
    enable_logging: bool = True         # Emit structured logs
    log_level: str = "INFO"            # Default log level for state changes

@dataclass 
class CircuitBreakerMetrics:
    """Metrics tracking for ERROR_MONITORING_SPEC integration."""
    total_requests: int = 0
    successful_requests: int = 0  
    failed_requests: int = 0
    rejected_requests: int = 0
    
    # State tracking
    state_transitions: Dict[str, int] = field(default_factory=dict)
    time_in_states: Dict[str, float] = field(default_factory=dict)
    last_state_change: Optional[datetime] = None
    
    # Performance metrics
    avg_response_time_ms: float = 0.0
    failure_rate: float = 0.0
    success_rate: float = 0.0
    
    # Provider-specific metrics  
    provider_name: str = ""
    circuit_name: str = ""
    
    def calculate_health_score(self) -> float:
        """Calculate overall health score for DEPLOYMENT_OPS_SPEC reporting."""
        if self.total_requests == 0:
            return 1.0
        
        success_factor = self.success_rate
        response_time_factor = max(0, 1.0 - (self.avg_response_time_ms / 10000))  # Penalize >10s responses
        rejection_factor = 1.0 - (self.rejected_requests / max(1, self.total_requests))
        
        return (success_factor * 0.5 + response_time_factor * 0.3 + rejection_factor * 0.2)
```

### 1.2 State Transition Logic
Implement precise state transitions with comprehensive logging:

```python
class CircuitBreakerStateMachine:
    """Core state machine for circuit breaker with monitoring integration."""
    
    def __init__(
        self, 
        name: str, 
        config: CircuitBreakerConfig,
        logger: Optional[logging.Logger] = None,
        metrics_collector: Optional[Any] = None
    ):
        self.name = name
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.metrics_collector = metrics_collector
        
        # State management
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
        
        # Thread safety
        self._lock = asyncio.Lock()
        
        # Metrics and monitoring
        self.metrics = CircuitBreakerMetrics(
            provider_name=name,
            circuit_name=name
        )
        self._state_change_history: List[tuple] = []
        self._rolling_window: List[Dict[str, Any]] = []
        
        # Initialize state tracking
        self._track_state_change(None, CircuitState.CLOSED, "initialization")
    
    async def can_execute(self, request_id: Optional[str] = None) -> bool:
        """Check if request can be executed through circuit breaker."""
        if not request_id:
            request_id = str(uuid.uuid4())
            
        async with self._lock:
            current_time = datetime.now()
            
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset(current_time):
                    await self._transition_to_half_open(request_id, current_time)
                    return self.half_open_calls < self.config.half_open_max_calls
                else:
                    self._log_request_rejected(request_id, "circuit_open")
                    self.metrics.rejected_requests += 1
                    return False
            
            elif self.state == CircuitState.HALF_OPEN:
                if self.half_open_calls >= self.config.half_open_max_calls:
                    self._log_request_rejected(request_id, "half_open_limit")
                    self.metrics.rejected_requests += 1
                    return False
                
                self.half_open_calls += 1
                return True
            
            # CLOSED state always allows requests
            return True
    
    async def record_success(self, request_id: str, response_time_ms: float):
        """Record successful execution with metrics tracking."""
        async with self._lock:
            current_time = datetime.now()
            
            # Update metrics
            self.metrics.total_requests += 1
            self.metrics.successful_requests += 1
            self.metrics.avg_response_time_ms = self._update_avg_response_time(response_time_ms)
            self.metrics.success_rate = self.metrics.successful_requests / self.metrics.total_requests
            
            # Update rolling window
            self._update_rolling_window(True, response_time_ms, current_time)
            
            # Reset failure count on success
            self.failure_count = 0
            self.last_success_time = current_time
            
            # State-specific handling
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                self._log_success_in_half_open(request_id)
                
                if self.success_count >= self.config.success_threshold:
                    await self._transition_to_closed(request_id, current_time)
            
            # Log success event for ERROR_MONITORING_SPEC
            if self.config.enable_logging:
                self._log_circuit_event(
                    "circuit_breaker_success",
                    request_id,
                    {
                        "response_time_ms": response_time_ms,
                        "success_count": self.success_count,
                        "total_requests": self.metrics.total_requests
                    }
                )
    
    async def record_failure(self, request_id: str, error: Exception, response_time_ms: float = 0):
        """Record failed execution with state transition logic."""
        async with self._lock:
            current_time = datetime.now()
            
            # Update metrics
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            if response_time_ms > 0:
                self.metrics.avg_response_time_ms = self._update_avg_response_time(response_time_ms)
            self.metrics.failure_rate = self.metrics.failed_requests / self.metrics.total_requests
            
            # Update rolling window
            self._update_rolling_window(False, response_time_ms, current_time)
            
            # State-specific failure handling
            if self.state == CircuitState.CLOSED:
                self.failure_count += 1
                self.last_failure_time = current_time
                
                if self._should_open_circuit():
                    await self._transition_to_open(request_id, current_time, error)
            
            elif self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open immediately opens circuit
                await self._transition_to_open(request_id, current_time, error)
                self.success_count = 0
            
            # Log failure event for ERROR_MONITORING_SPEC
            if self.config.enable_logging:
                self._log_circuit_event(
                    "circuit_breaker_failure",
                    request_id,
                    {
                        "error_type": type(error).__name__,
                        "error_message": str(error),
                        "failure_count": self.failure_count,
                        "response_time_ms": response_time_ms
                    },
                    level="WARNING"
                )
```

### 1.3 State Transition Methods
Implement clean state transitions with comprehensive monitoring:

```python
    async def _transition_to_open(self, request_id: str, timestamp: datetime, error: Exception):
        """Transition circuit to OPEN state with alert generation."""
        old_state = self.state
        self.state = CircuitState.OPEN
        self.failure_count = 0  # Reset for next cycle
        self.half_open_calls = 0
        
        self._track_state_change(old_state, CircuitState.OPEN, f"failure_threshold_exceeded: {str(error)}")
        
        # Generate critical alert for ERROR_MONITORING_SPEC
        self._log_circuit_event(
            "circuit_breaker_opened",
            request_id,
            {
                "trigger_error": str(error),
                "total_failures": self.metrics.failed_requests,
                "failure_rate": self.metrics.failure_rate,
                "time_until_retry": self.config.timeout_seconds
            },
            level="CRITICAL"
        )
        
        # Emit metrics for monitoring
        if self.config.enable_metrics and self.metrics_collector:
            self.metrics_collector.increment_counter(
                "circuit_breaker_state_transitions",
                tags={"circuit": self.name, "from_state": old_state.value, "to_state": "open"}
            )
    
    async def _transition_to_half_open(self, request_id: str, timestamp: datetime):
        """Transition circuit to HALF_OPEN state for recovery testing."""
        old_state = self.state
        self.state = CircuitState.HALF_OPEN
        self.half_open_calls = 0
        self.success_count = 0
        
        self._track_state_change(old_state, CircuitState.HALF_OPEN, "timeout_expired_attempting_recovery")
        
        self._log_circuit_event(
            "circuit_breaker_half_opened",
            request_id,
            {
                "recovery_attempt": True,
                "max_test_calls": self.config.half_open_max_calls,
                "required_successes": self.config.success_threshold
            },
            level="WARNING"
        )
    
    async def _transition_to_closed(self, request_id: str, timestamp: datetime):
        """Transition circuit to CLOSED state after successful recovery."""
        old_state = self.state
        self.state = CircuitState.CLOSED
        self.success_count = 0
        self.half_open_calls = 0
        
        self._track_state_change(old_state, CircuitState.CLOSED, "recovery_successful")
        
        self._log_circuit_event(
            "circuit_breaker_closed",
            request_id,
            {
                "recovery_successful": True,
                "current_success_rate": self.metrics.success_rate,
                "health_score": self.metrics.calculate_health_score()
            },
            level="INFO"
        )
    
    def _should_open_circuit(self) -> bool:
        """Determine if circuit should open based on failure count."""
        return self.failure_count >= self.config.failure_threshold
    
    def _should_attempt_reset(self, current_time: datetime) -> bool:
        """Check if enough time has passed for recovery attempt."""
        if not self.last_failure_time:
            return True
        
        time_since_failure = (current_time - self.last_failure_time).total_seconds()
        return time_since_failure >= self.config.timeout_seconds
    
    def _update_avg_response_time(self, new_response_time: float) -> float:
        """Update average response time using exponential moving average."""
        alpha = 0.1  # Smoothing factor
        if self.metrics.avg_response_time_ms == 0:
            return new_response_time
        return (alpha * new_response_time) + ((1 - alpha) * self.metrics.avg_response_time_ms)
    
    def _update_rolling_window(self, success: bool, response_time: float, timestamp: datetime):
        """Update rolling window for metrics calculation."""
        self._rolling_window.append({
            "timestamp": timestamp,
            "success": success,
            "response_time_ms": response_time
        })
        
        # Remove old entries beyond window size
        if len(self._rolling_window) > self.config.rolling_window_size:
            self._rolling_window.pop(0)
    
    def _track_state_change(self, from_state: Optional[CircuitState], to_state: CircuitState, reason: str):
        """Track state changes for monitoring and debugging."""
        self._state_change_history.append((from_state, to_state, datetime.now(), reason))
        self.metrics.last_state_change = datetime.now()
        
        # Update state transition counter
        transition_key = f"{from_state.value if from_state else 'init'}_to_{to_state.value}"
        self.metrics.state_transitions[transition_key] = self.metrics.state_transitions.get(transition_key, 0) + 1
    
    def _log_circuit_event(self, event_type: str, request_id: str, data: Dict[str, Any], level: str = "INFO"):
        """Log circuit breaker events for ERROR_MONITORING_SPEC integration."""
        if not self.config.enable_logging:
            return
            
        log_entry = {
            "event_type": event_type,
            "circuit_name": self.name,
            "circuit_state": self.state.value,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat(),
            **data
        }
        
        self.logger.log(
            getattr(logging, level),
            f"Circuit breaker event: {event_type}",
            extra={"structured": log_entry}
        )
    
    def _log_request_rejected(self, request_id: str, reason: str):
        """Log rejected requests for monitoring."""
        self._log_circuit_event(
            "circuit_breaker_request_rejected",
            request_id,
            {"rejection_reason": reason},
            level="WARNING"
        )
    
    def _log_success_in_half_open(self, request_id: str):
        """Log successful requests during half-open state."""
        self._log_circuit_event(
            "circuit_breaker_half_open_success",
            request_id,
            {
                "success_count": self.success_count,
                "required_successes": self.config.success_threshold
            }
        )
```

## 2. Failure Detection and Threshold Configuration

### 2.1 Failure Detection Framework
Implement sophisticated failure detection with provider-specific logic:

```python
from typing import Union, List, Type
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class FailureDetectionConfig:
    """Configuration for failure detection with provider-specific rules."""
    # Error classification
    retryable_errors: List[Type[Exception]] = field(default_factory=list)
    non_retryable_errors: List[Type[Exception]] = field(default_factory=list)
    timeout_errors: List[Type[Exception]] = field(default_factory=list)
    
    # Threshold configuration
    failure_threshold: int = 5
    failure_rate_threshold: float = 0.5  # 50% failure rate triggers opening
    response_time_threshold_ms: float = 10000  # 10s response time threshold
    
    # Time-based detection
    min_request_threshold: int = 10      # Minimum requests before rate calculation
    evaluation_window_seconds: int = 300  # 5-minute rolling window
    
    # Provider-specific overrides
    provider_specific_rules: Dict[str, Any] = field(default_factory=dict)

class FailureDetector(ABC):
    """Abstract base class for failure detection strategies."""
    
    @abstractmethod
    def is_failure(self, error: Exception, response_time_ms: float) -> bool:
        """Determine if an error/response constitutes a failure."""
        pass
    
    @abstractmethod
    def should_open_circuit(self, metrics: CircuitBreakerMetrics) -> bool:
        """Determine if circuit should open based on current metrics."""
        pass

class DefaultFailureDetector(FailureDetector):
    """Default failure detector with comprehensive error classification."""
    
    def __init__(self, config: FailureDetectionConfig):
        self.config = config
        self._setup_default_error_classifications()
    
    def is_failure(self, error: Exception, response_time_ms: float) -> bool:
        """Classify errors as failures with provider-specific logic."""
        error_type = type(error)
        
        # Non-retryable errors are always failures
        if any(issubclass(error_type, err_type) for err_type in self.config.non_retryable_errors):
            return True
        
        # Timeout-related failures
        if any(issubclass(error_type, err_type) for err_type in self.config.timeout_errors):
            return True
        
        # Response time threshold exceeded
        if response_time_ms > self.config.response_time_threshold_ms:
            return True
        
        # Check for retryable errors that might indicate systemic issues
        if any(issubclass(error_type, err_type) for err_type in self.config.retryable_errors):
            return self._is_systemic_failure(error)
        
        # Default: unknown errors are considered failures
        return True
    
    def should_open_circuit(self, metrics: CircuitBreakerMetrics) -> bool:
        """Multi-criteria circuit opening logic."""
        # Insufficient data
        if metrics.total_requests < self.config.min_request_threshold:
            return False
        
        # High failure rate
        if metrics.failure_rate >= self.config.failure_rate_threshold:
            return True
        
        # Consecutive failures threshold
        consecutive_failures = self._get_consecutive_failures(metrics)
        if consecutive_failures >= self.config.failure_threshold:
            return True
        
        # Average response time degradation
        if metrics.avg_response_time_ms > self.config.response_time_threshold_ms:
            return True
        
        return False
    
    def _setup_default_error_classifications(self):
        """Setup default error classifications for common providers."""
        # These would be imported from actual provider modules
        self.config.retryable_errors.extend([
            # Generic retryable errors
            TimeoutError,
            ConnectionError,
            # Add provider-specific retryable errors
        ])
        
        self.config.non_retryable_errors.extend([
            # Authentication/authorization failures
            PermissionError,
            ValueError,  # Invalid request format
            # Add provider-specific non-retryable errors
        ])
        
        self.config.timeout_errors.extend([
            TimeoutError,
            asyncio.TimeoutError,
        ])
    
    def _is_systemic_failure(self, error: Exception) -> bool:
        """Determine if retryable error indicates systemic issue."""
        # Implementation would check error patterns
        return True
    
    def _get_consecutive_failures(self, metrics: CircuitBreakerMetrics) -> int:
        """Get count of consecutive failures."""
        # Implementation would track consecutive failures
        return 0

class AIProviderFailureDetector(DefaultFailureDetector):
    """AI Provider-specific failure detector with enhanced logic."""
    
    def __init__(self, provider_name: str, config: FailureDetectionConfig):
        super().__init__(config)
        self.provider_name = provider_name
        self._setup_provider_specific_rules()
    
    def _setup_provider_specific_rules(self):
        """Setup provider-specific failure detection rules."""
        provider_rules = {
            "openai": {
                "rate_limit_retry_delay": 60,
                "model_overload_threshold": 3,
                "content_filter_failures": False  # Don't treat as circuit failures
            },
            "anthropic": {
                "rate_limit_retry_delay": 120,  
                "output_length_failures": False,
                "safety_filter_failures": False
            },
            "xai": {
                "beta_stability_threshold": 5,
                "format_consistency_weight": 0.8
            }
        }
        
        if self.provider_name.lower() in provider_rules:
            self.provider_rules = provider_rules[self.provider_name.lower()]
        else:
            self.provider_rules = {}
    
    def is_failure(self, error: Exception, response_time_ms: float) -> bool:
        """Provider-specific failure detection with enhanced logic."""
        # Check for provider-specific non-failure conditions
        if self._is_provider_specific_non_failure(error):
            return False
        
        # Apply base failure detection
        return super().is_failure(error, response_time_ms)
    
    def _is_provider_specific_non_failure(self, error: Exception) -> bool:
        """Check for provider-specific conditions that shouldn't trigger circuit."""
        error_message = str(error).lower()
        
        # OpenAI-specific non-failures
        if self.provider_name.lower() == "openai":
            if "content_filter" in error_message and not self.provider_rules.get("content_filter_failures", True):
                return True
        
        # Anthropic-specific non-failures  
        elif self.provider_name.lower() == "anthropic":
            if "safety" in error_message and not self.provider_rules.get("safety_filter_failures", True):
                return True
            if "output_length" in error_message and not self.provider_rules.get("output_length_failures", True):
                return True
        
        return False
```

### 2.2 Threshold Configuration System
Implement flexible threshold configuration with environment-based overrides:

```python
@dataclass
class ThresholdConfiguration:
    """Hierarchical threshold configuration with environment overrides."""
    
    # Base thresholds (can be overridden by environment/provider)
    base_failure_threshold: int = 5
    base_success_threshold: int = 2  
    base_timeout_seconds: int = 60
    
    # Provider-specific threshold overrides
    provider_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Environment-based scaling
    environment_multipliers: Dict[str, float] = field(default_factory=dict)
    
    # Dynamic threshold adjustment
    enable_adaptive_thresholds: bool = True
    adaptation_factor: float = 0.1  # How much to adjust based on history
    
    @classmethod
    def from_config(cls, config_dict: Dict[str, Any], environment: str = "production") -> "ThresholdConfiguration":
        """Create threshold configuration from config system."""
        instance = cls()
        
        # Apply base configuration
        if "thresholds" in config_dict:
            threshold_config = config_dict["thresholds"]
            instance.base_failure_threshold = threshold_config.get("failure_threshold", 5)
            instance.base_success_threshold = threshold_config.get("success_threshold", 2)
            instance.base_timeout_seconds = threshold_config.get("timeout_seconds", 60)
        
        # Apply provider-specific overrides
        if "provider_overrides" in config_dict:
            instance.provider_overrides = config_dict["provider_overrides"]
        
        # Apply environment multipliers
        if environment in config_dict.get("environment_multipliers", {}):
            instance.environment_multipliers = config_dict["environment_multipliers"][environment]
        
        return instance
    
    def get_failure_threshold(self, provider_name: str, environment: str = "production") -> int:
        """Get failure threshold with provider and environment overrides."""
        threshold = self.base_failure_threshold
        
        # Apply provider override
        if provider_name in self.provider_overrides:
            threshold = self.provider_overrides[provider_name].get("failure_threshold", threshold)
        
        # Apply environment multiplier
        if environment in self.environment_multipliers:
            threshold = int(threshold * self.environment_multipliers[environment])
        
        return max(1, threshold)  # Ensure minimum of 1
    
    def get_timeout_seconds(self, provider_name: str, environment: str = "production") -> int:
        """Get timeout with provider and environment overrides."""
        timeout = self.base_timeout_seconds
        
        # Apply provider override
        if provider_name in self.provider_overrides:
            timeout = self.provider_overrides[provider_name].get("timeout_seconds", timeout)
        
        # Apply environment multiplier  
        if environment in self.environment_multipliers:
            timeout = int(timeout * self.environment_multipliers[environment])
        
        return max(5, timeout)  # Ensure minimum of 5 seconds
```

## 3. Health Check Integration and Automatic Recovery

### 3.1 Health Check Framework Integration
Implement health check integration with DEPLOYMENT_OPS_SPEC endpoints:

```python
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum

class HealthStatus(Enum):
    """Health status aligned with DEPLOYMENT_OPS_SPEC HealthResponse."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    RECOVERING = "recovering"

@dataclass
class CircuitHealthReport:
    """Health report for DEPLOYMENT_OPS_SPEC integration."""
    circuit_name: str
    status: HealthStatus
    state: CircuitState
    
    # Health metrics
    health_score: float = 0.0
    success_rate: float = 0.0
    avg_response_time_ms: float = 0.0
    failure_count: int = 0
    
    # State information
    time_in_current_state: float = 0.0
    last_state_change: Optional[datetime] = None
    next_retry_time: Optional[datetime] = None
    
    # Additional context
    provider_name: str = ""
    error_summary: str = ""
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for DEPLOYMENT_OPS_SPEC health endpoint."""
        return {
            "circuit_name": self.circuit_name,
            "status": self.status.value,
            "circuit_state": self.state.value,
            "health_score": round(self.health_score, 3),
            "success_rate": round(self.success_rate, 3),
            "avg_response_time_ms": round(self.avg_response_time_ms, 2),
            "failure_count": self.failure_count,
            "time_in_current_state_seconds": round(self.time_in_current_state, 1),
            "last_state_change": self.last_state_change.isoformat() if self.last_state_change else None,
            "next_retry_time": self.next_retry_time.isoformat() if self.next_retry_time else None,
            "provider_name": self.provider_name,
            "error_summary": self.error_summary,
            "recommendations": self.recommendations
        }

class CircuitBreakerHealthChecker:
    """Health checker for circuit breakers with DEPLOYMENT_OPS_SPEC integration."""
    
    def __init__(self, circuit_breakers: Dict[str, CircuitBreakerStateMachine]):
        self.circuit_breakers = circuit_breakers
        self._health_history: Dict[str, List[CircuitHealthReport]] = defaultdict(list)
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall health status for DEPLOYMENT_OPS_SPEC /health endpoint."""
        individual_reports = self.get_individual_health_reports()
        
        # Calculate overall health
        total_circuits = len(individual_reports)
        healthy_circuits = sum(1 for report in individual_reports.values() 
                             if report.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED])
        
        overall_health_score = sum(report.health_score for report in individual_reports.values()) / max(1, total_circuits)
        
        # Determine overall status
        if healthy_circuits == total_circuits:
            overall_status = HealthStatus.HEALTHY
        elif healthy_circuits >= total_circuits * 0.7:  # 70% healthy threshold
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.UNHEALTHY
        
        return {
            "status": overall_status.value,
            "overall_health_score": round(overall_health_score, 3),
            "total_circuits": total_circuits,
            "healthy_circuits": healthy_circuits,
            "degraded_circuits": sum(1 for report in individual_reports.values() 
                                   if report.status == HealthStatus.DEGRADED),
            "unhealthy_circuits": sum(1 for report in individual_reports.values() 
                                    if report.status == HealthStatus.UNHEALTHY),
            "circuits": {name: report.to_dict() for name, report in individual_reports.items()},
            "timestamp": datetime.now().isoformat(),
            "sla_impact": self._calculate_sla_impact(individual_reports)
        }
    
    def get_individual_health_reports(self) -> Dict[str, CircuitHealthReport]:
        """Get health reports for individual circuit breakers."""
        reports = {}
        
        for name, circuit in self.circuit_breakers.items():
            report = self._generate_health_report(name, circuit)
            reports[name] = report
            
            # Store in history for trend analysis
            self._update_health_history(name, report)
        
        return reports
    
    def _generate_health_report(self, name: str, circuit: CircuitBreakerStateMachine) -> CircuitHealthReport:
        """Generate detailed health report for a single circuit breaker."""
        current_time = datetime.now()
        
        # Calculate time in current state
        time_in_state = 0.0
        if circuit._state_change_history:
            last_change = circuit._state_change_history[-1]
            time_in_state = (current_time - last_change[2]).total_seconds()
        
        # Determine health status based on circuit state and metrics
        status = self._determine_health_status(circuit)
        
        # Calculate next retry time for OPEN circuits
        next_retry_time = None
        if circuit.state == CircuitState.OPEN and circuit.last_failure_time:
            next_retry_time = circuit.last_failure_time + timedelta(seconds=circuit.config.timeout_seconds)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(circuit)
        
        return CircuitHealthReport(
            circuit_name=name,
            status=status,
            state=circuit.state,
            health_score=circuit.metrics.calculate_health_score(),
            success_rate=circuit.metrics.success_rate,
            avg_response_time_ms=circuit.metrics.avg_response_time_ms,
            failure_count=circuit.failure_count,
            time_in_current_state=time_in_state,
            last_state_change=circuit._state_change_history[-1][2] if circuit._state_change_history else None,
            next_retry_time=next_retry_time,
            provider_name=circuit.metrics.provider_name,
            error_summary=self._generate_error_summary(circuit),
            recommendations=recommendations
        )
    
    def _determine_health_status(self, circuit: CircuitBreakerStateMachine) -> HealthStatus:
        """Determine health status based on circuit state and metrics."""
        if circuit.state == CircuitState.CLOSED:
            if circuit.metrics.success_rate >= 0.95:
                return HealthStatus.HEALTHY
            elif circuit.metrics.success_rate >= 0.8:
                return HealthStatus.DEGRADED
            else:
                return HealthStatus.UNHEALTHY
        
        elif circuit.state == CircuitState.HALF_OPEN:
            return HealthStatus.RECOVERING
        
        else:  # OPEN state
            return HealthStatus.UNHEALTHY
    
    def _generate_recommendations(self, circuit: CircuitBreakerStateMachine) -> List[str]:
        """Generate actionable recommendations based on circuit state."""
        recommendations = []
        
        if circuit.state == CircuitState.OPEN:
            recommendations.append(f"Circuit will attempt recovery in {circuit.config.timeout_seconds}s")
            if circuit.metrics.failure_rate > 0.8:
                recommendations.append("Consider checking provider health and API status")
        
        elif circuit.state == CircuitState.HALF_OPEN:
            recommendations.append("Circuit is testing recovery - monitor closely")
        
        elif circuit.metrics.success_rate < 0.9:
            recommendations.append("Success rate below 90% - investigate error patterns")
        
        if circuit.metrics.avg_response_time_ms > 5000:
            recommendations.append("High response times detected - consider timeout adjustments")
        
        return recommendations
    
    def _generate_error_summary(self, circuit: CircuitBreakerStateMachine) -> str:
        """Generate error summary from recent failures."""
        if not circuit._rolling_window:
            return "No recent errors"
        
        # Analyze recent failures
        recent_failures = [entry for entry in circuit._rolling_window[-10:] if not entry.get("success", True)]
        if not recent_failures:
            return "No recent errors"
        
        return f"Recent failures: {len(recent_failures)} in last {len(circuit._rolling_window)} requests"
    
    def _calculate_sla_impact(self, reports: Dict[str, CircuitHealthReport]) -> Dict[str, Any]:
        """Calculate SLA impact for DEPLOYMENT_OPS_SPEC reporting."""
        unhealthy_count = sum(1 for r in reports.values() if r.status == HealthStatus.UNHEALTHY)
        degraded_count = sum(1 for r in reports.values() if r.status == HealthStatus.DEGRADED)
        
        # Calculate availability impact
        if unhealthy_count > 0:
            availability_impact = "HIGH"
            estimated_downtime_minutes = unhealthy_count * 5  # Rough estimate
        elif degraded_count > 0:
            availability_impact = "MEDIUM"
            estimated_downtime_minutes = degraded_count * 2
        else:
            availability_impact = "NONE"
            estimated_downtime_minutes = 0
        
        return {
            "availability_impact": availability_impact,
            "estimated_downtime_minutes": estimated_downtime_minutes,
            "sla_risk": availability_impact != "NONE",
            "affected_providers": [r.provider_name for r in reports.values() if r.status == HealthStatus.UNHEALTHY]
        }
    
    def _update_health_history(self, name: str, report: CircuitHealthReport):
        """Update health history for trend analysis."""
        self._health_history[name].append(report)
        
        # Keep only last 100 reports
        if len(self._health_history[name]) > 100:
            self._health_history[name] = self._health_history[name][-100:]
```

### 3.2 Automatic Recovery Mechanisms
Implement sophisticated recovery strategies with monitoring integration:

```python
@dataclass
class RecoveryStrategy:
    """Recovery strategy configuration with health check parameters."""
    name: str
    health_check_config: Dict[str, Any]
    timeout_seconds: int
    max_attempts: int
    backoff_multiplier: float = 1.5
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for recovery attempt."""
        return min(60, 1 * (self.backoff_multiplier ** attempt))

@dataclass 
class RecoveryAttempt:
    """Record of a recovery attempt for analysis and monitoring."""
    circuit_name: str
    attempt_time: datetime
    strategy_used: str
    request_id: str
    success: bool = False
    error: Optional[str] = None
    health_score: float = 0.0
    duration_seconds: float = 0.0

@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    success: bool
    health_score: float
    failure_reason: Optional[str] = None
    response_time_ms: float = 0.0

class AutomaticRecoveryManager:
    """Manages automatic recovery for circuit breakers with progressive strategies."""
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.recovery_strategies = self._load_recovery_strategies()
        self.recovery_history: Dict[str, List[RecoveryAttempt]] = defaultdict(list)
    
    async def attempt_recovery(self, circuit: CircuitBreakerStateMachine, request_id: str) -> bool:
        """Attempt circuit recovery with progressive strategy."""
        recovery_attempt = RecoveryAttempt(
            circuit_name=circuit.name,
            attempt_time=datetime.now(),
            strategy_used="progressive",
            request_id=request_id
        )
        
        start_time = time.time()
        
        try:
            # Determine recovery strategy based on failure history
            strategy = self._select_recovery_strategy(circuit)
            
            # Execute recovery strategy
            success = await self._execute_recovery_strategy(circuit, strategy, request_id)
            
            recovery_attempt.success = success
            recovery_attempt.strategy_used = strategy.name
            recovery_attempt.duration_seconds = time.time() - start_time
            
            # Log recovery attempt for ERROR_MONITORING_SPEC
            self._log_recovery_attempt(recovery_attempt)
            
            # Update recovery history
            self.recovery_history[circuit.name].append(recovery_attempt)
            
            return success
            
        except Exception as e:
            recovery_attempt.success = False
            recovery_attempt.error = str(e)
            recovery_attempt.duration_seconds = time.time() - start_time
            self._log_recovery_attempt(recovery_attempt)
            return False
    
    def _select_recovery_strategy(self, circuit: CircuitBreakerStateMachine) -> RecoveryStrategy:
        """Select recovery strategy based on circuit history and configuration."""
        failure_patterns = self._analyze_failure_patterns(circuit)
        recent_attempts = self.recovery_history[circuit.name][-5:]  # Last 5 attempts
        
        # Progressive strategy selection
        if len(recent_attempts) == 0:
            return self.recovery_strategies["gradual"]
        elif len(recent_attempts) < 3:
            return self.recovery_strategies["conservative"]
        else:
            # If multiple recent failures, use most conservative approach
            recent_failures = sum(1 for attempt in recent_attempts if not attempt.success)
            if recent_failures >= 3:
                return self.recovery_strategies["minimal"]
            else:
                return self.recovery_strategies["gradual"]
    
    async def _execute_recovery_strategy(
        self, 
        circuit: CircuitBreakerStateMachine, 
        strategy: RecoveryStrategy,
        request_id: str
    ) -> bool:
        """Execute specific recovery strategy with monitoring."""
        # Implement health check with strategy-specific parameters
        try:
            # Perform lightweight health check
            health_check_result = await self._perform_health_check(
                circuit, 
                strategy.health_check_config,
                request_id
            )
            
            if health_check_result.success:
                # Log successful recovery for ERROR_MONITORING_SPEC
                self.logger.info(
                    "Circuit recovery successful",
                    extra={
                        "circuit_name": circuit.name,
                        "strategy": strategy.name,
                        "request_id": request_id,
                        "health_score": health_check_result.health_score,
                        "response_time_ms": health_check_result.response_time_ms
                    }
                )
                return True
            else:
                # Log failed recovery attempt
                self.logger.warning(
                    "Circuit recovery failed", 
                    extra={
                        "circuit_name": circuit.name,
                        "strategy": strategy.name,
                        "request_id": request_id,
                        "failure_reason": health_check_result.failure_reason
                    }
                )
                return False
                
        except Exception as e:
            self.logger.error(
                "Circuit recovery error",
                extra={
                    "circuit_name": circuit.name,
                    "strategy": strategy.name,
                    "request_id": request_id,
                    "error": str(e)
                }
            )
            return False
    
    async def _perform_health_check(
        self, 
        circuit: CircuitBreakerStateMachine,
        config: Dict[str, Any],
        request_id: str
    ) -> HealthCheckResult:
        """Perform health check on the circuit's provider."""
        # This would be implemented with actual provider health check logic
        # For now, return a simulated result
        return HealthCheckResult(
            success=True,
            health_score=0.95,
            response_time_ms=150.0
        )
    
    def _load_recovery_strategies(self) -> Dict[str, RecoveryStrategy]:
        """Load recovery strategies from configuration."""
        return {
            "gradual": RecoveryStrategy(
                name="gradual",
                health_check_config={
                    "timeout": 5,
                    "test_payload": "minimal"
                },
                timeout_seconds=5,
                max_attempts=3,
                backoff_multiplier=1.2
            ),
            "conservative": RecoveryStrategy(
                name="conservative",
                health_check_config={
                    "timeout": 10,
                    "test_payload": "standard"
                },
                timeout_seconds=10,
                max_attempts=2,
                backoff_multiplier=2.0
            ),
            "minimal": RecoveryStrategy(
                name="minimal",
                health_check_config={
                    "timeout": 15,
                    "test_payload": "comprehensive"
                },
                timeout_seconds=15,
                max_attempts=1,
                backoff_multiplier=3.0
            )
        }
    
    def _analyze_failure_patterns(self, circuit: CircuitBreakerStateMachine) -> Dict[str, Any]:
        """Analyze failure patterns for strategy selection."""
        # Analyze recent failures from rolling window
        return {
            "consecutive_failures": circuit.failure_count,
            "failure_rate": circuit.metrics.failure_rate,
            "avg_response_time": circuit.metrics.avg_response_time_ms
        }
    
    def _log_recovery_attempt(self, attempt: RecoveryAttempt):
        """Log recovery attempt for monitoring."""
        self.logger.info(
            "Recovery attempt completed",
            extra={
                "circuit_name": attempt.circuit_name,
                "strategy": attempt.strategy_used,
                "success": attempt.success,
                "duration_seconds": attempt.duration_seconds,
                "request_id": attempt.request_id,
                "error": attempt.error
            }
        )
```

## 4. Metrics Collection and Monitoring Integration

### 4.1 Comprehensive Metrics Framework
Implement detailed metrics collection for ERROR_MONITORING_SPEC integration:

```python
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import time

@dataclass
class CircuitBreakerMetricsCollector:
    """Comprehensive metrics collector for circuit breaker monitoring."""
    
    # Prometheus-style metrics
    prometheus_metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Time-series data for trending
    metric_history: Dict[str, List[Any]] = field(default_factory=dict)
    
    # Aggregation windows
    aggregation_windows = [60, 300, 900, 3600]  # 1min, 5min, 15min, 1hour
    
    def __init__(self, circuit_name: str, enable_prometheus: bool = True):
        self.circuit_name = circuit_name
        self.enable_prometheus = enable_prometheus
        self._initialize_metrics()
    
    def _initialize_metrics(self):
        """Initialize Prometheus-style metrics for ERROR_MONITORING_SPEC integration."""
        base_labels = {"circuit": self.circuit_name}
        
        # Counter metrics
        self.prometheus_metrics.update({
            "circuit_breaker_requests_total": {
                "type": "counter",
                "help": "Total number of requests through circuit breaker",
                "labels": base_labels,
                "value": 0
            },
            "circuit_breaker_failures_total": {
                "type": "counter", 
                "help": "Total number of failed requests",
                "labels": base_labels,
                "value": 0
            },
            "circuit_breaker_rejections_total": {
                "type": "counter",
                "help": "Total number of rejected requests", 
                "labels": base_labels,
                "value": 0
            },
            "circuit_breaker_state_transitions_total": {
                "type": "counter",
                "help": "Total number of state transitions",
                "labels": base_labels,
                "value": 0
            }
        })
        
        # Gauge metrics
        self.prometheus_metrics.update({
            "circuit_breaker_state": {
                "type": "gauge",
                "help": "Current circuit breaker state (0=CLOSED, 1=HALF_OPEN, 2=OPEN)",
                "labels": base_labels,
                "value": 0
            },
            "circuit_breaker_failure_rate": {
                "type": "gauge", 
                "help": "Current failure rate (0.0-1.0)",
                "labels": base_labels,
                "value": 0.0
            },
            "circuit_breaker_health_score": {
                "type": "gauge",
                "help": "Overall health score (0.0-1.0)",
                "labels": base_labels, 
                "value": 1.0
            },
            "circuit_breaker_response_time_seconds": {
                "type": "gauge",
                "help": "Average response time in seconds",
                "labels": base_labels,
                "value": 0.0
            }
        })
        
        # Histogram metrics for response time distribution
        self.prometheus_metrics.update({
            "circuit_breaker_response_time_histogram": {
                "type": "histogram",
                "help": "Response time distribution",
                "labels": base_labels,
                "buckets": [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
                "values": {bucket: 0 for bucket in [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, float('inf')]}
            }
        })
    
    def record_request(self, success: bool, response_time_seconds: float, circuit_state: CircuitState):
        """Record a request with comprehensive metrics."""
        timestamp = datetime.now()
        
        # Update counters
        self.prometheus_metrics["circuit_breaker_requests_total"]["value"] += 1
        
        if not success:
            self.prometheus_metrics["circuit_breaker_failures_total"]["value"] += 1
        
        # Update response time histogram
        self._update_histogram("circuit_breaker_response_time_histogram", response_time_seconds)
        
        # Update gauges
        self._update_gauge("circuit_breaker_state", self._state_to_numeric(circuit_state))
        self._update_gauge("circuit_breaker_response_time_seconds", response_time_seconds)
        
        # Store time-series data
        self._store_time_series_data({
            "timestamp": timestamp,
            "success": success,
            "response_time_seconds": response_time_seconds,
            "circuit_state": circuit_state.value
        })
    
    def record_rejection(self, reason: str, circuit_state: CircuitState):
        """Record a rejected request."""
        self.prometheus_metrics["circuit_breaker_rejections_total"]["value"] += 1
        
        # Store rejection data for analysis
        self._store_time_series_data({
            "timestamp": datetime.now(),
            "rejection_reason": reason,
            "circuit_state": circuit_state.value,
            "type": "rejection"
        })
    
    def record_state_transition(self, from_state: CircuitState, to_state: CircuitState, reason: str):
        """Record state transition with detailed context."""
        self.prometheus_metrics["circuit_breaker_state_transitions_total"]["value"] += 1
        self._update_gauge("circuit_breaker_state", self._state_to_numeric(to_state))
        
        # Store transition data
        self._store_time_series_data({
            "timestamp": datetime.now(),
            "from_state": from_state.value,
            "to_state": to_state.value,
            "reason": reason,
            "type": "state_transition"
        })
    
    def calculate_windowed_metrics(self, window_seconds: int) -> Dict[str, Any]:
        """Calculate metrics for a specific time window."""
        cutoff_time = datetime.now() - timedelta(seconds=window_seconds)
        
        # Filter data within window
        window_data = [
            entry for entry in self.metric_history.get("requests", [])
            if entry["timestamp"] >= cutoff_time and entry.get("type") != "rejection"
        ]
        
        if not window_data:
            return {
                "window_seconds": window_seconds,
                "total_requests": 0,
                "success_rate": 1.0,
                "failure_rate": 0.0,
                "avg_response_time": 0.0,
                "p95_response_time": 0.0,
                "p99_response_time": 0.0
            }
        
        # Calculate metrics
        total_requests = len(window_data)
        successful_requests = sum(1 for entry in window_data if entry.get("success", False))
        success_rate = successful_requests / total_requests
        
        response_times = [entry.get("response_time_seconds", 0) for entry in window_data]
        response_times.sort()
        
        return {
            "window_seconds": window_seconds,
            "total_requests": total_requests,
            "success_rate": success_rate,
            "failure_rate": 1.0 - success_rate,
            "avg_response_time": sum(response_times) / len(response_times),
            "p95_response_time": response_times[int(len(response_times) * 0.95)] if response_times else 0,
            "p99_response_time": response_times[int(len(response_times) * 0.99)] if response_times else 0
        }
    
    def get_prometheus_metrics(self) -> str:
        """Generate Prometheus format metrics for ERROR_MONITORING_SPEC /metrics endpoint."""
        metrics_output = []
        
        for metric_name, metric_data in self.prometheus_metrics.items():
            metric_type = metric_data["type"]
            help_text = metric_data["help"]
            labels = metric_data["labels"]
            
            # Add metric metadata
            metrics_output.append(f"# HELP {metric_name} {help_text}")
            metrics_output.append(f"# TYPE {metric_name} {metric_type}")
            
            # Format labels
            label_str = ",".join([f'{k}="{v}"' for k, v in labels.items()])
            
            if metric_type == "histogram":
                # Special handling for histograms
                for bucket, count in metric_data["values"].items():
                    if bucket == float('inf'):
                        metrics_output.append(f'{metric_name}_bucket{{le="+Inf",{label_str}}} {count}')
                    else:
                        metrics_output.append(f'{metric_name}_bucket{{le="{bucket}",{label_str}}} {count}')
                
                # Add sum and count
                total_count = sum(metric_data["values"].values())
                metrics_output.append(f'{metric_name}_count{{{label_str}}} {total_count}')
                # Sum would need to be calculated from actual values
            else:
                # Regular counter/gauge
                metrics_output.append(f'{metric_name}{{{label_str}}} {metric_data["value"]}')
        
        return "\n".join(metrics_output)
    
    def _update_histogram(self, metric_name: str, value: float):
        """Update histogram metric with new value."""
        histogram = self.prometheus_metrics[metric_name]
        
        for bucket in histogram["buckets"]:
            if value <= bucket:
                histogram["values"][bucket] += 1
        
        # Always increment infinity bucket
        histogram["values"][float('inf')] += 1
    
    def _update_gauge(self, metric_name: str, value: float):
        """Update gauge metric."""
        self.prometheus_metrics[metric_name]["value"] = value
    
    def _state_to_numeric(self, state: CircuitState) -> int:
        """Convert circuit state to numeric value for Prometheus."""
        state_mapping = {
            CircuitState.CLOSED: 0,
            CircuitState.HALF_OPEN: 1, 
            CircuitState.OPEN: 2
        }
        return state_mapping.get(state, 0)
    
    def _store_time_series_data(self, data: Dict[str, Any]):
        """Store time-series data for trend analysis."""
        data_type = data.get("type", "requests")
        
        if data_type not in self.metric_history:
            self.metric_history[data_type] = []
        
        self.metric_history[data_type].append(data)
        
        # Cleanup old data (keep only last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.metric_history[data_type] = [
            entry for entry in self.metric_history[data_type]
            if entry["timestamp"] >= cutoff_time
        ]
```

## 5. Configuration and Testing Strategies

### 5.1 Configuration Management System
Implement flexible configuration with CONFIG_SYSTEM_SPEC integration:

```python
from typing import Dict, Any, Optional
import yaml
import json
from pathlib import Path

@dataclass
class CircuitBreakerGlobalConfig:
    """Global configuration for all circuit breakers with environment overrides."""
    
    # Default configurations
    default_failure_threshold: int = 5
    default_success_threshold: int = 2
    default_timeout_seconds: int = 60
    default_half_open_max_calls: int = 3
    
    # Environment-specific overrides
    environment_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Provider-specific configurations
    provider_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Monitoring configuration
    enable_metrics: bool = True
    enable_logging: bool = True
    metrics_export_interval: int = 30
    
    # Recovery configuration
    enable_auto_recovery: bool = True
    recovery_strategies: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def load_from_config_system(cls, config_path: str, environment: str = "production") -> "CircuitBreakerGlobalConfig":
        """Load configuration from CONFIG_SYSTEM_SPEC compliant file."""
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Circuit breaker config not found: {config_path}")
        
        # Load base configuration
        with open(config_file, 'r') as f:
            if config_file.suffix.lower() == '.yaml':
                config_data = yaml.safe_load(f)
            else:
                config_data = json.load(f)
        
        # Create instance with base config
        instance = cls()
        circuit_config = config_data.get("circuit_breakers", {})
        
        # Apply base settings
        if "defaults" in circuit_config:
            defaults = circuit_config["defaults"]
            instance.default_failure_threshold = defaults.get("failure_threshold", 5)
            instance.default_success_threshold = defaults.get("success_threshold", 2)
            instance.default_timeout_seconds = defaults.get("timeout_seconds", 60)
            instance.default_half_open_max_calls = defaults.get("half_open_max_calls", 3)
        
        # Apply environment overrides
        if "environments" in circuit_config:
            instance.environment_overrides = circuit_config["environments"]
        
        # Apply provider-specific configurations
        if "providers" in circuit_config:
            instance.provider_configs = circuit_config["providers"]
        
        # Apply monitoring configuration
        if "monitoring" in circuit_config:
            monitoring = circuit_config["monitoring"]
            instance.enable_metrics = monitoring.get("enable_metrics", True)
            instance.enable_logging = monitoring.get("enable_logging", True)
            instance.metrics_export_interval = monitoring.get("export_interval", 30)
        
        # Apply recovery configuration
        if "recovery" in circuit_config:
            recovery = circuit_config["recovery"]
            instance.enable_auto_recovery = recovery.get("enable_auto_recovery", True)
            instance.recovery_strategies = recovery.get("strategies", {})
        
        return instance
    
    def get_circuit_config(self, circuit_name: str, provider: str, environment: str = "production") -> CircuitBreakerConfig:
        """Get circuit breaker configuration for specific circuit/provider/environment."""
        config = CircuitBreakerConfig()
        
        # Start with defaults
        config.failure_threshold = self.default_failure_threshold
        config.success_threshold = self.default_success_threshold  
        config.timeout_seconds = self.default_timeout_seconds
        config.half_open_max_calls = self.default_half_open_max_calls
        
        # Apply provider-specific overrides
        if provider in self.provider_configs:
            provider_config = self.provider_configs[provider]
            config.failure_threshold = provider_config.get("failure_threshold", config.failure_threshold)
            config.success_threshold = provider_config.get("success_threshold", config.success_threshold)
            config.timeout_seconds = provider_config.get("timeout_seconds", config.timeout_seconds)
            config.half_open_max_calls = provider_config.get("half_open_max_calls", config.half_open_max_calls)
        
        # Apply environment overrides
        if environment in self.environment_overrides:
            env_config = self.environment_overrides[environment]
            multiplier = env_config.get("threshold_multiplier", 1.0)
            config.failure_threshold = int(config.failure_threshold * multiplier)
            config.timeout_seconds = int(config.timeout_seconds * env_config.get("timeout_multiplier", 1.0))
        
        # Apply monitoring settings
        config.enable_metrics = self.enable_metrics
        config.enable_logging = self.enable_logging
        
        return config

# Example configuration file structure (YAML)
EXAMPLE_CONFIG = """
circuit_breakers:
  defaults:
    failure_threshold: 5
    success_threshold: 2
    timeout_seconds: 60
    half_open_max_calls: 3
    response_time_threshold_ms: 10000
  
  environments:
    development:
      threshold_multiplier: 0.5  # More sensitive in dev
      timeout_multiplier: 2.0    # Longer timeouts in dev
    
    staging:
      threshold_multiplier: 0.8
      timeout_multiplier: 1.5
    
    production:
      threshold_multiplier: 1.0
      timeout_multiplier: 1.0
  
  providers:
    openai:
      failure_threshold: 3       # OpenAI is usually reliable
      timeout_seconds: 30        # Shorter timeout for OpenAI
      rate_limit_protection: true
    
    anthropic: 
      failure_threshold: 4
      timeout_seconds: 45
      response_time_threshold_ms: 15000  # Claude can be slower
    
    xai:
      failure_threshold: 6       # Beta service, more tolerant
      timeout_seconds: 90        # Longer timeout for beta
      beta_tolerance: true
  
  monitoring:
    enable_metrics: true
    enable_logging: true
    export_interval: 30
    prometheus_port: 9090
    
    alerts:
      circuit_open:
        severity: critical
        notify_channels: ["slack", "email"]
      
      high_failure_rate:
        threshold: 0.3
        severity: warning
        notify_channels: ["slack"]
  
  recovery:
    enable_auto_recovery: true
    strategies:
      gradual:
        health_check_timeout: 5
        max_attempts: 3
        backoff_multiplier: 1.2
      
      conservative:
        health_check_timeout: 10
        max_attempts: 2  
        backoff_multiplier: 2.0
      
      minimal:
        health_check_timeout: 15
        max_attempts: 1
        backoff_multiplier: 3.0
"""
```

### 5.2 Comprehensive Testing Framework
Implement testing strategies that cover all circuit breaker scenarios:

```python
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from typing import List, Dict, Any
import random

class CircuitBreakerTestSuite:
    """Comprehensive test suite for circuit breaker functionality."""
    
    def __init__(self):
        self.test_scenarios = self._define_test_scenarios()
        self.mock_providers = {}
        self.test_metrics = {}
    
    def _define_test_scenarios(self) -> List[Dict[str, Any]]:
        """Define comprehensive test scenarios for circuit breaker behavior."""
        return [
            {
                "name": "normal_operation",
                "description": "Circuit remains closed under normal conditions",
                "setup": {
                    "failure_threshold": 5,
                    "success_rate": 0.95,
                    "request_count": 100
                },
                "expected_state": CircuitState.CLOSED,
                "expected_rejections": 0
            },
            {
                "name": "gradual_failure_increase", 
                "description": "Circuit opens when failure threshold exceeded",
                "setup": {
                    "failure_threshold": 5,
                    "initial_success_rate": 0.9,
                    "final_success_rate": 0.2,
                    "request_count": 50
                },
                "expected_state": CircuitState.OPEN,
                "expected_transitions": ["CLOSED", "OPEN"]
            },
            {
                "name": "timeout_based_failures",
                "description": "Circuit opens due to timeout failures",
                "setup": {
                    "failure_threshold": 3,
                    "timeout_rate": 0.8,
                    "request_count": 20
                },
                "expected_state": CircuitState.OPEN,
                "expected_alert_level": "CRITICAL"
            },
            {
                "name": "recovery_success",
                "description": "Circuit recovers from OPEN to CLOSED via HALF_OPEN",
                "setup": {
                    "start_state": CircuitState.OPEN,
                    "recovery_success_rate": 1.0,
                    "recovery_request_count": 3
                },
                "expected_state": CircuitState.CLOSED,
                "expected_transitions": ["OPEN", "HALF_OPEN", "CLOSED"]
            },
            {
                "name": "recovery_failure",
                "description": "Circuit returns to OPEN if recovery fails",
                "setup": {
                    "start_state": CircuitState.OPEN,
                    "recovery_success_rate": 0.0,
                    "recovery_request_count": 1
                },
                "expected_state": CircuitState.OPEN,
                "expected_transitions": ["OPEN", "HALF_OPEN", "OPEN"]
            },
            {
                "name": "high_load_stability",
                "description": "Circuit behaves correctly under high load",
                "setup": {
                    "concurrent_requests": 100,
                    "success_rate": 0.85,
                    "duration_seconds": 30
                },
                "expected_max_response_time": 5.0,
                "expected_state": CircuitState.CLOSED
            },
            {
                "name": "provider_specific_thresholds",
                "description": "Different providers use appropriate thresholds",
                "setup": {
                    "providers": ["openai", "anthropic", "xai"],
                    "provider_configs": {
                        "openai": {"failure_threshold": 3},
                        "anthropic": {"failure_threshold": 4},
                        "xai": {"failure_threshold": 6}
                    }
                },
                "validate_provider_differences": True
            }
        ]
    
    async def run_scenario_test(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """Run a specific test scenario with comprehensive validation."""
        scenario_name = scenario["name"]
        print(f"Running scenario: {scenario_name}")
        
        # Setup test environment
        circuit = await self._setup_test_circuit(scenario)
        mock_provider = self._create_mock_provider(scenario)
        
        test_result = {
            "scenario": scenario_name,
            "success": False,
            "details": {},
            "metrics": {},
            "errors": []
        }
        
        try:
            # Execute scenario
            if scenario_name == "normal_operation":
                await self._test_normal_operation(circuit, mock_provider, scenario, test_result)
            elif scenario_name == "gradual_failure_increase":
                await self._test_gradual_failure_increase(circuit, mock_provider, scenario, test_result)
            elif scenario_name == "timeout_based_failures":
                await self._test_timeout_failures(circuit, mock_provider, scenario, test_result)
            elif scenario_name == "recovery_success":
                await self._test_recovery_success(circuit, mock_provider, scenario, test_result)
            elif scenario_name == "recovery_failure":
                await self._test_recovery_failure(circuit, mock_provider, scenario, test_result)
            elif scenario_name == "high_load_stability":
                await self._test_high_load_stability(circuit, mock_provider, scenario, test_result)
            elif scenario_name == "provider_specific_thresholds":
                await self._test_provider_specific_thresholds(scenario, test_result)
            
            # Validate results
            test_result["success"] = self._validate_scenario_results(scenario, test_result)
            
        except Exception as e:
            test_result["errors"].append(f"Scenario execution failed: {str(e)}")
            test_result["success"] = False
        
        return test_result
    
    async def _test_normal_operation(self, circuit, mock_provider, scenario, test_result):
        """Test circuit behavior under normal operating conditions."""
        setup = scenario["setup"]
        request_count = setup["request_count"]
        success_rate = setup["success_rate"]
        
        successful_requests = 0
        failed_requests = 0
        rejected_requests = 0
        
        for i in range(request_count):
            request_id = f"test_request_{i}"
            
            # Check if circuit allows request
            can_execute = await circuit.can_execute(request_id)
            
            if can_execute:
                # Simulate request execution
                if random.random() < success_rate:
                    await circuit.record_success(request_id, random.uniform(50, 200))
                    successful_requests += 1
                else:
                    await circuit.record_failure(request_id, Exception("Simulated failure"), random.uniform(100, 500))
                    failed_requests += 1
            else:
                rejected_requests += 1
        
        test_result["details"] = {
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "rejected_requests": rejected_requests,
            "final_state": circuit.state.value,
            "success_rate": successful_requests / (successful_requests + failed_requests) if (successful_requests + failed_requests) > 0 else 0
        }
        
        test_result["metrics"] = {
            "total_requests": circuit.metrics.total_requests,
            "final_failure_rate": circuit.metrics.failure_rate,
            "health_score": circuit.metrics.calculate_health_score()
        }
    
    async def _test_recovery_success(self, circuit, mock_provider, scenario, test_result):
        """Test successful recovery from OPEN to CLOSED state."""
        setup = scenario["setup"]
        
        # Force circuit to OPEN state
        circuit.state = CircuitState.OPEN
        circuit.last_failure_time = datetime.now() - timedelta(seconds=circuit.config.timeout_seconds + 1)
        
        state_transitions = []
        recovery_requests = setup["recovery_request_count"]
        success_rate = setup["recovery_success_rate"]
        
        for i in range(recovery_requests):
            request_id = f"recovery_request_{i}"
            
            # Record initial state
            initial_state = circuit.state.value
            
            can_execute = await circuit.can_execute(request_id)
            
            if can_execute:
                if random.random() < success_rate:
                    await circuit.record_success(request_id, random.uniform(50, 150))
                else:
                    await circuit.record_failure(request_id, Exception("Recovery failure"))
            
            # Record state after request
            final_state = circuit.state.value
            if initial_state != final_state:
                state_transitions.append(f"{initial_state} -> {final_state}")
        
        test_result["details"] = {
            "state_transitions": state_transitions,
            "final_state": circuit.state.value,
            "recovery_requests_executed": recovery_requests
        }

    def _validate_scenario_results(self, scenario: Dict[str, Any], test_result: Dict[str, Any]) -> bool:
        """Validate test results against expected outcomes."""
        if "expected_state" in scenario:
            expected_state = scenario["expected_state"]
            actual_state = CircuitState(test_result["details"]["final_state"])
            if actual_state != expected_state:
                test_result["errors"].append(f"Expected state {expected_state.value}, got {actual_state.value}")
                return False
        
        if "expected_rejections" in scenario:
            expected_rejections = scenario["expected_rejections"]
            actual_rejections = test_result["details"].get("rejected_requests", 0)
            if actual_rejections != expected_rejections:
                test_result["errors"].append(f"Expected {expected_rejections} rejections, got {actual_rejections}")
                return False
        
        if "expected_transitions" in scenario:
            expected_transitions = scenario["expected_transitions"]
            actual_transitions = test_result["details"].get("state_transitions", [])
            # Validate that expected transitions occurred
            for expected in expected_transitions:
                if not any(expected in transition for transition in actual_transitions):
                    test_result["errors"].append(f"Expected transition involving {expected} not found")
                    return False
        
        return len(test_result["errors"]) == 0
    
    async def _setup_test_circuit(self, scenario: Dict[str, Any]) -> CircuitBreakerStateMachine:
        """Setup circuit breaker for testing."""
        config = CircuitBreakerConfig()
        
        if "setup" in scenario:
            setup = scenario["setup"]
            config.failure_threshold = setup.get("failure_threshold", 5)
            config.success_threshold = setup.get("success_threshold", 2)
            config.timeout_seconds = setup.get("timeout_seconds", 5)
        
        return CircuitBreakerStateMachine(
            name="test_circuit",
            config=config,
            logger=Mock(),
            metrics_collector=Mock()
        )
    
    def _create_mock_provider(self, scenario: Dict[str, Any]) -> Mock:
        """Create mock provider for testing."""
        mock_provider = Mock()
        mock_provider.name = "test_provider"
        return mock_provider

# Integration test configuration
@pytest.fixture
async def circuit_breaker_test_environment():
    """Setup comprehensive test environment for circuit breaker testing."""
    config = CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout_seconds=5,
        half_open_max_calls=2
    )
    
    # Create mock logger and metrics collector
    mock_logger = Mock()
    mock_metrics = Mock()
    
    circuit = CircuitBreakerStateMachine(
        name="test_circuit",
        config=config,
        logger=mock_logger,
        metrics_collector=mock_metrics
    )
    
    yield {
        "circuit": circuit,
        "config": config,
        "logger": mock_logger,
        "metrics": mock_metrics
    }

# Example pytest tests
@pytest.mark.asyncio
async def test_circuit_breaker_normal_operation(circuit_breaker_test_environment):
    """Test circuit breaker under normal operating conditions."""
    env = circuit_breaker_test_environment
    circuit = env["circuit"]
    
    # Execute successful requests
    for i in range(10):
        request_id = f"request_{i}"
        assert await circuit.can_execute(request_id)
        await circuit.record_success(request_id, 100.0)
    
    # Verify circuit remains closed
    assert circuit.state == CircuitState.CLOSED
    assert circuit.metrics.success_rate == 1.0
    assert circuit.failure_count == 0

@pytest.mark.asyncio
async def test_circuit_breaker_failure_threshold(circuit_breaker_test_environment):
    """Test circuit opens when failure threshold is exceeded."""
    env = circuit_breaker_test_environment
    circuit = env["circuit"]
    
    # Execute failures up to threshold
    for i in range(circuit.config.failure_threshold):
        request_id = f"failure_request_{i}"
        assert await circuit.can_execute(request_id)
        await circuit.record_failure(request_id, Exception(f"Test failure {i}"))
    
    # Verify circuit is now open
    assert circuit.state == CircuitState.OPEN
    
    # Verify subsequent requests are rejected
    assert not await circuit.can_execute("rejected_request")
```

## Implementation Priorities and Success Criteria

### Implementation Priorities
1. **Core State Machine Implementation** - Implement the three-state circuit breaker with proper state transitions and ERROR_MONITORING_SPEC logging integration
2. **Failure Detection Framework** - Create sophisticated failure detection with provider-specific rules and threshold configuration
3. **Health Check Integration** - Integrate with DEPLOYMENT_OPS_SPEC health endpoints and automatic recovery mechanisms
4. **Metrics Collection** - Implement comprehensive metrics collection for ERROR_MONITORING_SPEC Prometheus integration
5. **Configuration System** - Create flexible configuration management with CONFIG_SYSTEM_SPEC hot-reload support
6. **Testing Framework** - Develop comprehensive testing strategies covering all failure and recovery scenarios

### Success Criteria
- **State Transition Accuracy**: 100% correct state transitions with proper logging to ERROR_MONITORING_SPEC
- **Failure Detection Precision**: <5% false positive rate in failure detection with provider-specific tuning
- **Recovery Time Optimization**: Mean recovery time <30 seconds for healthy providers
- **Metrics Integration**: All metrics properly exposed via /metrics endpoint for DEPLOYMENT_OPS_SPEC monitoring
- **Configuration Flexibility**: Support for environment and provider-specific configuration overrides
- **Test Coverage**: >95% test coverage for all circuit breaker scenarios including edge cases
- **Performance Impact**: <5ms overhead per request when circuit is CLOSED
- **SLA Compliance**: Circuit breaker decisions must support 99% uptime SLA requirements

## Critical Integration Points

### ERROR_MONITORING_SPEC Alignment
- All circuit breaker events must include request IDs for end-to-end tracing
- State transitions must emit structured logs with appropriate severity levels
- Metrics must be exposed via Prometheus format at /metrics endpoint
- Alert generation must follow defined severity and escalation patterns

### AI_PROVIDER_SPEC Integration
- Circuit breakers must protect all AI providers (OpenAI, Anthropic, X.ai) with provider-specific configurations
- Provider health must be tracked and reported via circuit breaker metrics
- Fallback provider selection must be supported when primary providers are circuit broken
- Rate limit protection must prevent cascading failures across providers

### DEPLOYMENT_OPS_SPEC Health Reporting
- Circuit breaker health must be exposed via /health and /ready endpoints
- Circuit state must contribute to overall system health scoring
- SLA impact must be calculated and reported for monitoring dashboards
- Graceful degradation signals must be provided for load balancer integration

This specification provides a comprehensive foundation for implementing a robust circuit breaker system that integrates seamlessly with all SizeComparator components while providing excellent observability, configurability, and reliability under various failure conditions.