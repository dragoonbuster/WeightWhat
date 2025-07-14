"""
Abstract base provider class for AI providers.

Implements the core provider contract from AI_PROVIDER_SPEC with circuit breaker,
retry logic, and health monitoring integration.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypeVar, Callable
from uuid import uuid4
import random

from ..models.providers import (
    AIProviderRequest, AIProviderResponse, AIProviderHealth,
    ProviderStatus, CircuitBreakerState, AIProviderMetadata,
    ProviderConfiguration
)
from ..models.responses import WeightComparisonResponse
from ..core.monitoring import get_logger, get_metrics, request_context
from ..core.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from ..core.exceptions import AIProviderException, RateLimitException, ValidationException


T = TypeVar('T')


class RetryConfig:
    """Configuration for retry logic with exponential backoff."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay_ms: int = 100,
        max_delay_ms: int = 10000,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.initial_delay_ms = initial_delay_ms
        self.max_delay_ms = max_delay_ms
        self.exponential_base = exponential_base
        self.jitter = jitter


class ProviderCapabilities:
    """Capabilities and limits for a provider."""
    
    def __init__(
        self,
        max_tokens: int = 4000,
        supports_json_mode: bool = True,
        supports_streaming: bool = False,
        rate_limit_rpm: Optional[int] = None,
        rate_limit_tpm: Optional[int] = None,
        supports_function_calling: bool = False
    ):
        self.max_tokens = max_tokens
        self.supports_json_mode = supports_json_mode
        self.supports_streaming = supports_streaming
        self.rate_limit_rpm = rate_limit_rpm
        self.rate_limit_tpm = rate_limit_tpm
        self.supports_function_calling = supports_function_calling


class AIProviderBase(ABC):
    """
    Abstract base class for AI provider implementations.
    
    Provides circuit breaker, retry logic, health monitoring, and
    standardized error handling as per AI_PROVIDER_SPEC.
    """
    
    def __init__(
        self, 
        config: ProviderConfiguration,
        capabilities: ProviderCapabilities,
        retry_config: Optional[RetryConfig] = None,
        logger: Optional[Any] = None,
        metrics: Optional[Any] = None
    ):
        self.config = config
        self.capabilities = capabilities
        self.retry_config = retry_config or RetryConfig()
        self.name = config.provider_name
        self.logger = logger or get_logger()
        self.metrics = metrics or get_metrics()
        
        # Initialize health tracking
        self._health = AIProviderHealth(
            provider_name=self.name,
            status=ProviderStatus.HEALTHY,
            circuit_breaker_state=CircuitBreakerState.CLOSED,
            success_rate=1.0,
            avg_response_time_ms=0.0,
            error_count=0,
            requests_per_minute=0,
            circuit_breaker_config={
                'failure_threshold': 5,
                'success_threshold': 2,
                'timeout_seconds': 60
            }
        )
        
        # Performance tracking
        self._request_times: List[float] = []
        self._success_count = 0
        self._total_count = 0
        self._last_minute_requests: List[datetime] = []
        
        # Initialize circuit breaker if enabled
        self._circuit_breaker: Optional[CircuitBreaker] = None
        if config.circuit_breaker_enabled:
            cb_config = CircuitBreakerConfig(
                **config.circuit_breaker_config,
                expected_exception=AIProviderException
            )
            self._circuit_breaker = CircuitBreaker(
                name=f"{self.name}_circuit_breaker",
                config=cb_config,
                logger=self.logger,
                metrics=self.metrics
            )
        
        # Initialize provider-specific resources
        self._initialize()
    
    @abstractmethod
    def _initialize(self):
        """Initialize provider-specific resources (clients, connections, etc)."""
        pass
    
    @abstractmethod
    async def _generate_comparison_impl(
        self,
        request: AIProviderRequest
    ) -> Dict[str, Any]:
        """
        Provider-specific implementation of comparison generation.
        
        Returns raw provider response that will be parsed and validated.
        """
        pass
    
    @abstractmethod
    def _validate_response(self, response: Any) -> bool:
        """Validate provider-specific response format."""
        pass
    
    @abstractmethod
    def _parse_response(
        self,
        response: Any,
        request: AIProviderRequest
    ) -> WeightComparisonResponse:
        """Parse provider-specific response into standard format."""
        pass
    
    async def generate_comparison(
        self,
        request: AIProviderRequest
    ) -> WeightComparisonResponse:
        """
        Generate weight comparison using provider with full error handling.
        
        Includes circuit breaker, retry logic, and monitoring integration.
        """
        start_time = time.time()
        
        # Set request context for tracing
        request_context.set_request_id(str(request.request_id))
        request_context.set_context(
            provider=self.name,
            prompt_template=request.prompt_template_id
        )
        
        try:
            # Execute with circuit breaker if enabled
            if self._circuit_breaker:
                response = await self._circuit_breaker.call(
                    self._execute_with_retry,
                    request
                )
            else:
                response = await self._execute_with_retry(request)
            
            # Record success
            duration_ms = (time.time() - start_time) * 1000
            self._record_success(duration_ms)
            
            return response
            
        except Exception as e:
            # Record failure
            duration_ms = (time.time() - start_time) * 1000
            self._record_failure(duration_ms, e)
            
            # Log structured error
            self._log_structured_event(
                "error",
                f"Provider {self.name} failed to generate comparison",
                error_type=type(e).__name__,
                error_message=str(e),
                request_id=str(request.request_id),
                duration_ms=duration_ms
            )
            
            raise
    
    async def _execute_with_retry(self, request: AIProviderRequest) -> WeightComparisonResponse:
        """Execute request with exponential backoff retry."""
        last_error = None
        
        for attempt in range(self.retry_config.max_attempts):
            try:
                # Log attempt
                self._log_structured_event(
                    "debug",
                    f"Provider {self.name} attempt {attempt + 1}/{self.retry_config.max_attempts}",
                    request_id=str(request.request_id),
                    attempt=attempt + 1
                )
                
                # Execute provider-specific implementation
                response = await self._generate_comparison_impl(request)
                
                # Validate response
                if not self._validate_response(response):
                    raise ValidationException(
                        "Invalid response format from provider",
                        details={'provider': self.name, 'response': str(response)[:200]}
                    )
                
                # Parse into standard format
                parsed_response = self._parse_response(response, request)
                
                return parsed_response
                
            except RateLimitException as e:
                # Always retry rate limit errors with backoff
                last_error = e
                await self._handle_rate_limit(e, attempt)
                
            except AIProviderException as e:
                # Retry provider errors based on configuration
                last_error = e
                if attempt < self.retry_config.max_attempts - 1:
                    delay = self._calculate_backoff_delay(attempt)
                    await asyncio.sleep(delay / 1000)
                else:
                    raise
                    
            except Exception as e:
                # Don't retry unexpected errors
                raise AIProviderException(
                    f"Unexpected error from provider {self.name}",
                    details={'error': str(e), 'type': type(e).__name__}
                )
        
        # All retries exhausted
        raise last_error or AIProviderException(
            f"Provider {self.name} failed after {self.retry_config.max_attempts} attempts"
        )
    
    def _calculate_backoff_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay with optional jitter."""
        delay = self.retry_config.initial_delay_ms * (
            self.retry_config.exponential_base ** attempt
        )
        
        # Cap at max delay
        delay = min(delay, self.retry_config.max_delay_ms)
        
        # Add jitter to prevent thundering herd
        if self.retry_config.jitter:
            delay = delay * (0.5 + random.random() * 0.5)
        
        return delay
    
    async def _handle_rate_limit(self, error: RateLimitException, attempt: int):
        """Handle rate limit errors with appropriate backoff."""
        retry_after = getattr(error, 'retry_after', None)
        
        if retry_after:
            # Use provider-specified retry time
            delay_ms = retry_after * 1000
        else:
            # Use exponential backoff
            delay_ms = self._calculate_backoff_delay(attempt + 1)
        
        self._log_structured_event(
            "warning",
            f"Rate limit hit for provider {self.name}, waiting {delay_ms}ms",
            request_id=request_context.get_request_id(),
            retry_after_ms=delay_ms
        )
        
        await asyncio.sleep(delay_ms / 1000)
    
    def _record_success(self, duration_ms: float):
        """Record successful request for health tracking."""
        self._total_count += 1
        self._success_count += 1
        self._request_times.append(duration_ms)
        self._last_minute_requests.append(datetime.now(timezone.utc))
        
        # Update health metrics
        self._update_health_metrics()
        
        # Update metrics if available
        if hasattr(self.metrics, 'record_ai_provider_request'):
            self.metrics.record_ai_provider_request(
                provider=self.name,
                status="success",
                duration=duration_ms / 1000  # Convert to seconds
            )
    
    def _record_failure(self, duration_ms: float, error: Exception):
        """Record failed request for health tracking."""
        self._total_count += 1
        self._health.error_count += 1
        self._health.last_error = str(error)[:500]
        
        # Update health metrics
        self._update_health_metrics()
        
        # Update metrics if available
        if hasattr(self.metrics, 'record_ai_provider_request'):
            self.metrics.record_ai_provider_request(
                provider=self.name,
                status="failure",
                duration=duration_ms / 1000  # Convert to seconds
            )
    
    def _update_health_metrics(self):
        """Update provider health metrics."""
        # Clean up old request times
        cutoff = datetime.now(timezone.utc).timestamp() - 60
        self._last_minute_requests = [
            ts for ts in self._last_minute_requests 
            if ts.timestamp() > cutoff
        ]
        
        # Calculate metrics
        if self._total_count > 0:
            self._health.success_rate = self._success_count / self._total_count
        
        if self._request_times:
            # Keep last 100 request times for averaging
            self._request_times = self._request_times[-100:]
            self._health.avg_response_time_ms = sum(self._request_times) / len(self._request_times)
        
        self._health.requests_per_minute = len(self._last_minute_requests)
        
        # Update status based on success rate
        if self._health.success_rate < 0.5:
            self._health.status = ProviderStatus.UNHEALTHY
        elif self._health.success_rate < 0.9:
            self._health.status = ProviderStatus.DEGRADED
        else:
            self._health.status = ProviderStatus.HEALTHY
        
        # Update circuit breaker state if available
        if self._circuit_breaker:
            cb_state = self._circuit_breaker.get_state()
            self._health.circuit_breaker_state = CircuitBreakerState(cb_state.value)
    
    def get_health_status(self) -> AIProviderHealth:
        """Return current provider health for monitoring."""
        self._update_health_metrics()
        return self._health
    
    async def health_check(self) -> bool:
        """
        Perform provider-specific health check.
        
        Tests basic connectivity and response parsing.
        """
        try:
            test_request = AIProviderRequest(
                prompt_template_id="health_check",
                template_variables={
                    "item1_name": "Test Item 1",
                    "item1_weight": "10 kg",
                    "item2_name": "Test Item 2",
                    "item2_weight": "5 kg",
                    "weight_ratio": 2.0,
                    "percentage_difference": 100.0,
                    "heavier_item": "Test Item 1",
                    "comparison_category": "object_vs_object",
                    "significance_level": "significant",
                    "output_unit": "kg",
                    "locale": "en-US"
                },
                weight_data={
                    "item1": {"weight_kg": 10.0},
                    "item2": {"weight_kg": 5.0}
                },
                max_tokens=150,
                temperature=0.7,
                timeout_seconds=5.0
            )
            
            # Use lower-level implementation to avoid circuit breaker
            response = await self._generate_comparison_impl(test_request)
            
            # Just validate we can parse the response
            return self._validate_response(response)
            
        except Exception as e:
            self._log_structured_event(
                "error",
                f"Health check failed for provider {self.name}",
                error=str(e),
                request_id=str(uuid4())
            )
            return False
    
    def _log_structured_event(self, level: str, message: str, **kwargs):
        """Log structured events for monitoring integration."""
        log_data = {
            "provider": self.name,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_context.get_request_id(),
            **kwargs
        }
        getattr(self.logger, level)(message, extra=log_data)
    
    async def shutdown(self):
        """Cleanup provider resources."""
        self._log_structured_event(
            "info",
            f"Shutting down provider {self.name}"
        )
    
    # Lifecycle hooks for subclasses
    async def on_startup(self):
        """Initialize provider resources on startup."""
        pass
    
    async def on_error(self, error: Exception):
        """Handle provider-specific errors."""
        pass
    
    async def on_rate_limit(self, retry_after: float):
        """Handle rate limit with provider-specific logic."""
        pass