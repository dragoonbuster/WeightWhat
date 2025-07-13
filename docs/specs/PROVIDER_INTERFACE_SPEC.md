# Provider Interface Specification

## Overview

This specification defines the abstract base class and contracts that all AI providers (OpenAI, Anthropic, X.ai) must implement for the SizeComparator system. The interface ensures consistent behavior, reliability, and seamless integration across different AI providers while supporting extensibility for future providers.

## Abstract Base Class Definition

### Core AIProvider Interface

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
import asyncio

from pydantic import BaseModel, Field, validator
from weight_spec import Weight
from comparison_spec import Comparison, ComparisonResponse


class ProviderHealth(BaseModel):
    """Health status model for AI providers"""
    status: str = Field(..., pattern="^(healthy|degraded|unhealthy)$")
    latency_ms: float = Field(..., ge=0)
    success_rate: float = Field(..., ge=0, le=1)
    last_check: datetime
    error_count: int = Field(default=0, ge=0)
    details: Dict[str, Any] = Field(default_factory=dict)


class ProviderConfig(BaseModel):
    """Base configuration for all providers"""
    api_key: str = Field(..., min_length=1)
    timeout_seconds: float = Field(default=30.0, gt=0)
    max_retries: int = Field(default=3, ge=0)
    retry_delay_base: float = Field(default=1.0, gt=0)
    circuit_breaker_threshold: int = Field(default=5, ge=1)
    circuit_breaker_timeout: float = Field(default=60.0, gt=0)
    
    class Config:
        extra = "allow"  # Allow provider-specific fields


class AIProvider(ABC):
    """Abstract base class for all AI provider implementations"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self._health = ProviderHealth(
            status="healthy",
            latency_ms=0,
            success_rate=1.0,
            last_check=datetime.utcnow()
        )
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=config.circuit_breaker_threshold,
            recovery_timeout=config.circuit_breaker_timeout
        )
        self._metrics = ProviderMetrics()
    
    @abstractmethod
    async def generate_comparisons(self, weight: Weight) -> List[Comparison]:
        """
        Generate exactly 2 comparisons for the given weight.
        
        Args:
            weight: Weight object to generate comparisons for
            
        Returns:
            List of exactly 2 Comparison objects
            
        Raises:
            ProviderError: For provider-specific errors
            ValidationError: If response validation fails
            TimeoutError: If request exceeds timeout
        """
        pass
    
    @abstractmethod
    def validate_response(self, response: Any) -> bool:
        """
        Validate provider-specific response format and content.
        
        Args:
            response: Raw response from the AI provider
            
        Returns:
            True if response is valid, False otherwise
        """
        pass
    
    @abstractmethod
    def parse_response(self, raw_response: str) -> ComparisonResponse:
        """
        Parse raw response into structured ComparisonResponse.
        
        Args:
            raw_response: Raw string response from provider
            
        Returns:
            Parsed ComparisonResponse object
            
        Raises:
            ParseError: If response cannot be parsed
        """
        pass
    
    def get_health_status(self) -> ProviderHealth:
        """
        Get current health status of the provider.
        
        Returns:
            ProviderHealth object with current status
        """
        return self._health.copy(deep=True)
    
    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """
        Perform active health check on the provider.
        
        Returns:
            Updated ProviderHealth status
        """
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize provider resources and validate configuration.
        
        Raises:
            ConfigurationError: If configuration is invalid
            ConnectionError: If provider cannot be reached
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """
        Gracefully shutdown provider and cleanup resources.
        """
        pass
    
    async def reload_config(self, new_config: ProviderConfig) -> None:
        """
        Hot-reload configuration without service interruption.
        
        Args:
            new_config: New configuration to apply
        """
        old_config = self.config
        try:
            self.config = new_config
            await self._apply_config_changes(old_config, new_config)
        except Exception as e:
            self.config = old_config
            raise ConfigurationError(f"Failed to reload config: {e}")
    
    @abstractmethod
    async def _apply_config_changes(
        self, 
        old_config: ProviderConfig, 
        new_config: ProviderConfig
    ) -> None:
        """Apply provider-specific configuration changes."""
        pass


class ProviderError(Exception):
    """Base exception for provider-specific errors"""
    def __init__(self, message: str, provider: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.provider = provider
        self.retry_after = retry_after


class ValidationError(ProviderError):
    """Raised when response validation fails"""
    pass


class ParseError(ProviderError):
    """Raised when response parsing fails"""
    pass
```

## Provider Lifecycle Management

### Initialization Patterns

```python
class ProviderLifecycleManager:
    """Manages provider lifecycle with dependency injection"""
    
    def __init__(self, config_source: ConfigSource, metrics_sink: MetricsSink):
        self.config_source = config_source
        self.metrics_sink = metrics_sink
        self.providers: Dict[str, AIProvider] = {}
        self._shutdown_handlers: List[Callable] = []
    
    async def initialize_provider(
        self, 
        provider_class: Type[AIProvider], 
        provider_name: str
    ) -> AIProvider:
        """
        Initialize a provider with full dependency injection.
        
        Steps:
        1. Load configuration from CONFIG_SYSTEM_SPEC
        2. Create provider instance
        3. Initialize provider resources
        4. Register health check
        5. Start metrics collection
        """
        config = await self.config_source.get_provider_config(provider_name)
        provider = provider_class(config)
        
        try:
            await provider.initialize()
            await self._register_health_check(provider, provider_name)
            self._start_metrics_collection(provider, provider_name)
            self.providers[provider_name] = provider
            return provider
        except Exception as e:
            await provider.shutdown()
            raise ProviderError(f"Failed to initialize {provider_name}: {e}", provider_name)
    
    async def shutdown_provider(self, provider_name: str) -> None:
        """
        Gracefully shutdown a provider with cleanup.
        
        Steps:
        1. Stop accepting new requests
        2. Wait for in-flight requests (max 30s)
        3. Close connections
        4. Cleanup resources
        5. Deregister health checks
        """
        if provider_name not in self.providers:
            return
            
        provider = self.providers[provider_name]
        
        # Stop new requests
        provider._accepting_requests = False
        
        # Wait for in-flight requests
        await self._wait_for_requests(provider, timeout=30)
        
        # Shutdown provider
        await provider.shutdown()
        
        # Cleanup
        await self._deregister_health_check(provider_name)
        self._stop_metrics_collection(provider_name)
        del self.providers[provider_name]
    
    async def reload_provider_config(self, provider_name: str) -> None:
        """Hot-reload provider configuration without downtime."""
        if provider_name not in self.providers:
            raise ValueError(f"Provider {provider_name} not initialized")
            
        new_config = await self.config_source.get_provider_config(provider_name)
        await self.providers[provider_name].reload_config(new_config)
    
    async def recover_provider(self, provider_name: str) -> None:
        """
        Attempt to recover a failed provider.
        
        Steps:
        1. Shutdown existing instance
        2. Wait for cleanup
        3. Reinitialize with fresh config
        4. Verify health before marking as available
        """
        provider_class = self._get_provider_class(provider_name)
        
        # Shutdown if exists
        if provider_name in self.providers:
            await self.shutdown_provider(provider_name)
        
        # Wait before restart
        await asyncio.sleep(5)
        
        # Reinitialize
        provider = await self.initialize_provider(provider_class, provider_name)
        
        # Verify health
        health = await provider.health_check()
        if health.status != "healthy":
            raise ProviderError(
                f"Provider {provider_name} unhealthy after recovery", 
                provider_name
            )
```

## Circuit Breaker Integration

### Circuit Breaker Implementation

```python
class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Rejecting requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Circuit breaker for provider reliability"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.success_count = 0
        self._lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        async with self._lock:
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise CircuitOpenError("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise
    
    async def _on_success(self) -> None:
        """Handle successful call."""
        async with self._lock:
            self.failure_count = 0
            
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= 3:  # Require 3 successes
                    self.state = CircuitState.CLOSED
                    self.success_count = 0
    
    async def _on_failure(self) -> None:
        """Handle failed call."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.success_count = 0
            elif self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset."""
        if not self.last_failure_time:
            return False
            
        time_since_failure = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return time_since_failure >= self.recovery_timeout
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "can_reset": self._should_attempt_reset()
        }


class CircuitBreakerMixin:
    """Mixin for providers to integrate circuit breaker"""
    
    async def _execute_with_circuit_breaker(
        self, 
        func: Callable, 
        *args, 
        **kwargs
    ) -> Any:
        """Execute provider function with circuit breaker protection."""
        return await self._circuit_breaker.call(func, *args, **kwargs)
    
    async def check_circuit_health(self) -> Dict[str, Any]:
        """Get circuit breaker health for monitoring."""
        state = self._circuit_breaker.get_state()
        
        # Integrate with DEPLOYMENT_OPS_SPEC health endpoints
        health_data = {
            "circuit_state": state["state"],
            "is_available": state["state"] != "open",
            "failure_count": state["failure_count"],
            "last_failure": state["last_failure"],
            "metrics": {
                "total_requests": self._metrics.total_requests,
                "failed_requests": self._metrics.failed_requests,
                "success_rate": self._metrics.get_success_rate()
            }
        }
        
        return health_data
```

## Response Validation Framework

### Quality Scoring and Validation

```python
class QualityScore(BaseModel):
    """Quality assessment for AI responses"""
    overall_score: float = Field(..., ge=0, le=1)
    relevance_score: float = Field(..., ge=0, le=1)
    accuracy_score: float = Field(..., ge=0, le=1)
    safety_score: float = Field(..., ge=0, le=1)
    details: Dict[str, Any] = Field(default_factory=dict)


class ValidationFramework:
    """Comprehensive response validation framework"""
    
    def __init__(self):
        self.validators: List[ResponseValidator] = [
            StructureValidator(),
            ContentValidator(),
            MathematicalValidator(),
            SafetyValidator()
        ]
    
    async def validate_response(
        self, 
        response: ComparisonResponse, 
        weight: Weight
    ) -> ValidationResult:
        """
        Perform comprehensive validation on response.
        
        Validations:
        1. Structure - Exactly 2 comparisons
        2. Content - Appropriate object selection
        3. Mathematical - Weight relationships correct
        4. Safety - No inappropriate content
        """
        results = []
        
        for validator in self.validators:
            result = await validator.validate(response, weight)
            results.append(result)
        
        return self._aggregate_results(results)
    
    def calculate_quality_score(
        self, 
        response: ComparisonResponse, 
        weight: Weight
    ) -> QualityScore:
        """Calculate 0.0-1.0 quality score for response."""
        scores = {
            "relevance": self._score_relevance(response, weight),
            "accuracy": self._score_accuracy(response, weight),
            "safety": self._score_safety(response)
        }
        
        overall = sum(scores.values()) / len(scores)
        
        return QualityScore(
            overall_score=overall,
            relevance_score=scores["relevance"],
            accuracy_score=scores["accuracy"],
            safety_score=scores["safety"],
            details={"weight_grams": weight.grams, "comparisons": len(response.comparisons)}
        )


class ResponseValidator(ABC):
    """Base validator interface"""
    
    @abstractmethod
    async def validate(
        self, 
        response: ComparisonResponse, 
        weight: Weight
    ) -> ValidationResult:
        """Validate specific aspect of response."""
        pass


class StructureValidator(ResponseValidator):
    """Validates response structure requirements"""
    
    async def validate(
        self, 
        response: ComparisonResponse, 
        weight: Weight
    ) -> ValidationResult:
        if len(response.comparisons) != 2:
            return ValidationResult(
                is_valid=False,
                error=f"Expected 2 comparisons, got {len(response.comparisons)}"
            )
        
        for comp in response.comparisons:
            if not comp.object_name or not comp.quantity:
                return ValidationResult(
                    is_valid=False,
                    error="Missing object name or quantity"
                )
        
        return ValidationResult(is_valid=True)


class MathematicalValidator(ResponseValidator):
    """Validates mathematical accuracy"""
    
    async def validate(
        self, 
        response: ComparisonResponse, 
        weight: Weight
    ) -> ValidationResult:
        for comp in response.comparisons:
            # Verify weight calculations
            calculated_weight = comp.quantity * comp.typical_weight_grams
            
            # Allow 10% margin for approximations
            margin = weight.grams * 0.1
            if abs(calculated_weight - weight.grams) > margin:
                return ValidationResult(
                    is_valid=False,
                    error=f"Mathematical error: {comp.quantity} × {comp.typical_weight_grams}g ≠ {weight.grams}g"
                )
        
        return ValidationResult(is_valid=True)


class SafetyValidator(ResponseValidator):
    """Validates content safety"""
    
    def __init__(self):
        self.inappropriate_terms = load_safety_filter_terms()
    
    async def validate(
        self, 
        response: ComparisonResponse, 
        weight: Weight
    ) -> ValidationResult:
        for comp in response.comparisons:
            if self._contains_inappropriate_content(comp):
                return ValidationResult(
                    is_valid=False,
                    error="Response contains inappropriate content"
                )
        
        return ValidationResult(is_valid=True)
    
    def _contains_inappropriate_content(self, comparison: Comparison) -> bool:
        """Check for inappropriate content in comparison."""
        text = f"{comparison.object_name} {comparison.visual_description}"
        return any(term in text.lower() for term in self.inappropriate_terms)
```

## Error Handling and Retry Logic

### Error Categorization and Retry Strategy

```python
class ErrorCategory(Enum):
    """Provider error categories for retry decisions"""
    RATE_LIMIT = "rate_limit"      # Retry with backoff
    TIMEOUT = "timeout"             # Retry immediately
    INVALID_REQUEST = "invalid_request"  # Don't retry
    SERVER_ERROR = "server_error"   # Retry with backoff
    NETWORK_ERROR = "network_error" # Retry immediately
    AUTHENTICATION = "authentication"  # Don't retry


class RetryStrategy(ABC):
    """Base retry strategy interface"""
    
    @abstractmethod
    def should_retry(self, error: ProviderError, attempt: int) -> bool:
        """Determine if request should be retried."""
        pass
    
    @abstractmethod
    def get_delay(self, attempt: int) -> float:
        """Calculate delay before next retry."""
        pass


class ExponentialBackoffStrategy(RetryStrategy):
    """Exponential backoff with jitter"""
    
    def __init__(self, base_delay: float = 1.0, max_delay: float = 60.0, max_retries: int = 3):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
    
    def should_retry(self, error: ProviderError, attempt: int) -> bool:
        if attempt >= self.max_retries:
            return False
            
        category = self._categorize_error(error)
        return category in [
            ErrorCategory.RATE_LIMIT,
            ErrorCategory.TIMEOUT,
            ErrorCategory.SERVER_ERROR,
            ErrorCategory.NETWORK_ERROR
        ]
    
    def get_delay(self, attempt: int) -> float:
        # Exponential backoff: base * 2^attempt
        delay = self.base_delay * (2 ** attempt)
        
        # Add jitter (±25%)
        import random
        jitter = delay * 0.25 * (2 * random.random() - 1)
        delay += jitter
        
        return min(delay, self.max_delay)
    
    def _categorize_error(self, error: ProviderError) -> ErrorCategory:
        """Categorize error for retry decision."""
        # Provider implementations override this
        return ErrorCategory.SERVER_ERROR


class ErrorHandler:
    """Comprehensive error handling with retry logic"""
    
    def __init__(self, retry_strategy: RetryStrategy, logger: StructuredLogger):
        self.retry_strategy = retry_strategy
        self.logger = logger
    
    async def execute_with_retry(
        self,
        func: Callable,
        provider_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with retry logic and error handling.
        
        Integrates with ERROR_MONITORING_SPEC for structured logging.
        """
        last_error = None
        
        for attempt in range(self.retry_strategy.max_retries + 1):
            try:
                # Add timeout handling
                timeout = kwargs.pop('timeout', 30.0)
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout
                )
                
            except asyncio.TimeoutError as e:
                last_error = ProviderError(
                    f"Request timeout after {timeout}s",
                    provider_name
                )
                self._log_error(last_error, attempt, ErrorCategory.TIMEOUT)
                
            except ProviderError as e:
                last_error = e
                category = self._categorize_error(e)
                self._log_error(e, attempt, category)
                
                if not self.retry_strategy.should_retry(e, attempt):
                    break
                    
                if e.retry_after:
                    await asyncio.sleep(e.retry_after)
                else:
                    delay = self.retry_strategy.get_delay(attempt)
                    await asyncio.sleep(delay)
                    
            except Exception as e:
                # Unexpected error
                last_error = ProviderError(
                    f"Unexpected error: {str(e)}",
                    provider_name
                )
                self._log_error(last_error, attempt, ErrorCategory.SERVER_ERROR)
                break
        
        # All retries exhausted
        raise last_error
    
    def _log_error(
        self, 
        error: ProviderError, 
        attempt: int, 
        category: ErrorCategory
    ) -> None:
        """Log error with ERROR_MONITORING_SPEC format."""
        self.logger.error(
            "provider_error",
            provider=error.provider,
            attempt=attempt,
            category=category.value,
            error_message=str(error),
            retry_after=error.retry_after,
            stack_trace=self._get_stack_trace()
        )


class TimeoutHandler:
    """Handle request timeouts and cancellations"""
    
    def __init__(self, default_timeout: float = 30.0):
        self.default_timeout = default_timeout
        self._active_requests: Dict[str, asyncio.Task] = {}
    
    async def execute_with_timeout(
        self,
        request_id: str,
        func: Callable,
        timeout: Optional[float] = None,
        *args,
        **kwargs
    ) -> Any:
        """Execute with timeout and cancellation support."""
        timeout = timeout or self.default_timeout
        
        task = asyncio.create_task(func(*args, **kwargs))
        self._active_requests[request_id] = task
        
        try:
            return await asyncio.wait_for(task, timeout=timeout)
        except asyncio.TimeoutError:
            await self.cancel_request(request_id)
            raise
        finally:
            self._active_requests.pop(request_id, None)
    
    async def cancel_request(self, request_id: str) -> bool:
        """Cancel an active request."""
        if request_id in self._active_requests:
            task = self._active_requests[request_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            return True
        return False
```

## Configuration and Testing Integration

### Provider Configuration and Extensibility

```python
class ProviderRegistry:
    """Registry for provider implementations with CONFIG_SYSTEM_SPEC integration"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self._providers: Dict[str, Type[AIProvider]] = {}
        self._mock_providers: Dict[str, Type[AIProvider]] = {}
    
    def register_provider(
        self, 
        name: str, 
        provider_class: Type[AIProvider],
        is_mock: bool = False
    ) -> None:
        """Register a provider implementation."""
        if is_mock:
            self._mock_providers[name] = provider_class
        else:
            self._providers[name] = provider_class
    
    def get_provider_class(self, name: str, use_mock: bool = False) -> Type[AIProvider]:
        """Get provider class with mock support for TESTING_SPEC."""
        if use_mock and name in self._mock_providers:
            return self._mock_providers[name]
        
        if name not in self._providers:
            raise ValueError(f"Unknown provider: {name}")
            
        return self._providers[name]
    
    async def create_provider(
        self, 
        name: str, 
        config_override: Optional[Dict[str, Any]] = None,
        use_mock: bool = False
    ) -> AIProvider:
        """Create provider instance with configuration."""
        provider_class = self.get_provider_class(name, use_mock)
        
        # Load configuration from CONFIG_SYSTEM_SPEC
        config_dict = await self.config_manager.get_provider_config(name)
        
        if config_override:
            config_dict.update(config_override)
        
        # Create provider-specific config
        config = self._create_provider_config(name, config_dict)
        
        return provider_class(config)


class MockProvider(AIProvider):
    """Mock provider for testing"""
    
    def __init__(self, config: ProviderConfig, responses: List[ComparisonResponse]):
        super().__init__(config)
        self.responses = responses
        self.call_count = 0
        self.last_weight = None
    
    async def generate_comparisons(self, weight: Weight) -> List[Comparison]:
        self.last_weight = weight
        self.call_count += 1
        
        if self.call_count <= len(self.responses):
            response = self.responses[self.call_count - 1]
            return response.comparisons
        
        # Default response
        return [
            Comparison(
                object_name="Test Object 1",
                quantity=1,
                total_weight=weight.grams,
                typical_weight_grams=weight.grams,
                visual_description="Test description 1"
            ),
            Comparison(
                object_name="Test Object 2",  
                quantity=2,
                total_weight=weight.grams,
                typical_weight_grams=weight.grams / 2,
                visual_description="Test description 2"
            )
        ]


class ProviderMetrics:
    """Performance monitoring for providers"""
    
    def __init__(self):
        self.total_requests = 0
        self.failed_requests = 0
        self.total_latency_ms = 0.0
        self.latencies: List[float] = []
        self._lock = asyncio.Lock()
    
    async def record_request(
        self, 
        success: bool, 
        latency_ms: float,
        error_type: Optional[str] = None
    ) -> None:
        """Record request metrics."""
        async with self._lock:
            self.total_requests += 1
            if not success:
                self.failed_requests += 1
            
            self.total_latency_ms += latency_ms
            self.latencies.append(latency_ms)
            
            # Keep only last 1000 latencies
            if len(self.latencies) > 1000:
                self.latencies.pop(0)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics for monitoring."""
        success_rate = (self.total_requests - self.failed_requests) / max(1, self.total_requests)
        avg_latency = self.total_latency_ms / max(1, self.total_requests)
        
        return {
            "total_requests": self.total_requests,
            "failed_requests": self.failed_requests,
            "success_rate": success_rate,
            "average_latency_ms": avg_latency,
            "p50_latency_ms": self._percentile(self.latencies, 0.5),
            "p95_latency_ms": self._percentile(self.latencies, 0.95),
            "p99_latency_ms": self._percentile(self.latencies, 0.99)
        }


# Extension Pattern Example
class NewAIProvider(AIProvider):
    """Example of extending for a new provider"""
    
    async def generate_comparisons(self, weight: Weight) -> List[Comparison]:
        # Implementation specific to new provider
        async with self._execute_with_circuit_breaker(self._make_request, weight) as response:
            validated = self.validate_response(response)
            if not validated:
                raise ValidationError("Invalid response format", self.__class__.__name__)
            
            return self.parse_response(response).comparisons
    
    def validate_response(self, response: Any) -> bool:
        # Provider-specific validation
        return hasattr(response, 'choices') and len(response.choices) > 0
    
    def parse_response(self, raw_response: str) -> ComparisonResponse:
        # Provider-specific parsing
        pass
```

## Summary

This provider interface specification establishes a robust, extensible framework for integrating multiple AI providers into the SizeComparator system. Key features include:

1. **Abstract Base Class**: Complete AIProvider interface with all required methods for comparison generation, validation, and health monitoring

2. **Lifecycle Management**: Comprehensive initialization, shutdown, configuration reload, and recovery procedures

3. **Circuit Breaker**: Integrated fault tolerance with automatic state management and recovery testing

4. **Validation Framework**: Multi-layer validation including structure, content, mathematical accuracy, and safety filtering

5. **Error Handling**: Sophisticated retry logic with exponential backoff, timeout handling, and structured error categorization

6. **Extensibility**: Clear patterns for adding new providers while maintaining consistent behavior across the system

The interface ensures reliability through circuit breakers, maintainability through clear contracts, and performance through integrated monitoring and metrics collection.