"""
Circuit breaker implementation with monitoring integration.

Implements AI_PROVIDER_SPEC circuit breaker states (CLOSED, OPEN, HALF_OPEN)
with metrics collection and alerting for the ERROR_MONITORING_SPEC system.
"""

import asyncio
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from .monitoring import CircuitBreakerState, ErrorSeverity, get_logger, get_metrics
from .exceptions import CircuitBreakerOpenException, AIProviderException


class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: int = 60,
        half_open_max_calls: int = 3,
        expected_exception: type = Exception
    ):
        """
        Initialize circuit breaker configuration.
        
        Args:
            failure_threshold: Number of failures before opening circuit (default from AI_PROVIDER_SPEC)
            success_threshold: Number of successes needed to close from half-open (default from AI_PROVIDER_SPEC)
            timeout_seconds: Time to wait before transitioning to half-open (default from AI_PROVIDER_SPEC)
            half_open_max_calls: Maximum calls allowed in half-open state
            expected_exception: Exception type that triggers circuit breaker
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds
        self.half_open_max_calls = half_open_max_calls
        self.expected_exception = expected_exception


class CircuitBreakerStats:
    """Statistics tracking for circuit breaker."""
    
    def __init__(self):
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.last_success_time: Optional[float] = None
        self.state_change_time = time.time()
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0
        self.half_open_calls = 0
    
    def record_success(self):
        """Record a successful call."""
        self.success_count += 1
        self.total_successes += 1
        self.total_calls += 1
        self.last_success_time = time.time()
    
    def record_failure(self):
        """Record a failed call."""
        self.failure_count += 1
        self.total_failures += 1
        self.total_calls += 1
        self.last_failure_time = time.time()
    
    def reset_counts(self):
        """Reset success and failure counts."""
        self.failure_count = 0
        self.success_count = 0
        self.half_open_calls = 0
    
    def get_failure_rate(self) -> float:
        """Get failure rate percentage."""
        if self.total_calls == 0:
            return 0.0
        return (self.total_failures / self.total_calls) * 100
    
    def get_success_rate(self) -> float:
        """Get success rate percentage."""
        if self.total_calls == 0:
            return 100.0
        return (self.total_successes / self.total_calls) * 100


class CircuitBreaker:
    """
    Circuit breaker implementation with monitoring integration.
    
    Implements the exact states from AI_PROVIDER_SPEC:
    - CLOSED: Normal operation
    - OPEN: Failing fast, rejecting calls
    - HALF_OPEN: Testing if service has recovered
    
    Integrates with ERROR_MONITORING_SPEC for metrics and alerting.
    """
    
    def __init__(
        self,
        name: str,
        config: CircuitBreakerConfig,
        logger=None,
        metrics=None
    ):
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.stats = CircuitBreakerStats()
        self.logger = logger or get_logger()
        self.metrics = metrics or get_metrics()
        self._lock = asyncio.Lock()
        
        # Initialize metrics
        self.metrics.set_circuit_breaker_state("sizecomparator", self.name, self.state)
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenException: When circuit is open
            Original exception: When function fails
        """
        async with self._lock:
            # Check if we should transition state
            await self._check_state_transition()
            
            # Handle different states
            if self.state == CircuitBreakerState.OPEN:
                self._log_call_blocked()
                raise CircuitBreakerOpenException(
                    f"Circuit breaker '{self.name}' is OPEN",
                    details={'provider': self.name, 'state': self.state.value}
                )
            
            if self.state == CircuitBreakerState.HALF_OPEN:
                if self.stats.half_open_calls >= self.config.half_open_max_calls:
                    self._log_call_blocked()
                    raise CircuitBreakerOpenException(
                        f"Circuit breaker '{self.name}' HALF_OPEN call limit exceeded",
                        details={'provider': self.name, 'state': self.state.value}
                    )
                
                self.stats.half_open_calls += 1
        
        # Execute the function
        try:
            start_time = time.time()
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            duration = time.time() - start_time
            
            await self._on_success(duration)
            return result
            
        except Exception as exc:
            duration = time.time() - start_time
            await self._on_failure(exc, duration)
            raise
    
    async def _check_state_transition(self):
        """Check if circuit breaker should transition state."""
        now = time.time()
        
        if self.state == CircuitBreakerState.OPEN:
            # Check if timeout has passed to transition to HALF_OPEN
            if (now - self.stats.state_change_time) >= self.config.timeout_seconds:
                await self._transition_to_half_open()
        
        elif self.state == CircuitBreakerState.CLOSED:
            # Check if failure threshold exceeded to transition to OPEN
            if self.stats.failure_count >= self.config.failure_threshold:
                await self._transition_to_open()
        
        elif self.state == CircuitBreakerState.HALF_OPEN:
            # Check if success threshold met to transition to CLOSED
            if self.stats.success_count >= self.config.success_threshold:
                await self._transition_to_closed()
    
    async def _on_success(self, duration: float):
        """Handle successful call."""
        async with self._lock:
            self.stats.record_success()
            
            # Reset failure count on success
            if self.state == CircuitBreakerState.CLOSED:
                self.stats.failure_count = 0
            
            # Log success
            self.logger.debug(
                f"Circuit breaker '{self.name}' call succeeded",
                provider_name=self.name,
                circuit_breaker_state=self.state.value,
                duration_seconds=duration,
                success_count=self.stats.success_count
            )
            
            # Check for state transition
            await self._check_state_transition()
    
    async def _on_failure(self, exception: Exception, duration: float):
        """Handle failed call."""
        async with self._lock:
            # Only count expected exceptions as failures
            if isinstance(exception, self.config.expected_exception):
                self.stats.record_failure()
                
                # Reset success count on failure
                if self.state == CircuitBreakerState.HALF_OPEN:
                    self.stats.success_count = 0
                
                # Log failure
                self.logger.warning(
                    f"Circuit breaker '{self.name}' call failed",
                    provider_name=self.name,
                    circuit_breaker_state=self.state.value,
                    duration_seconds=duration,
                    failure_count=self.stats.failure_count,
                    error_type=exception.__class__.__name__,
                    error_message=str(exception)
                )
                
                # Check for state transition
                await self._check_state_transition()
    
    async def _transition_to_open(self):
        """Transition circuit breaker to OPEN state."""
        old_state = self.state
        self.state = CircuitBreakerState.OPEN
        self.stats.state_change_time = time.time()
        
        # Update metrics
        self.metrics.set_circuit_breaker_state("sizecomparator", self.name, self.state)
        
        # Log state change
        self.logger.critical(
            f"Circuit breaker '{self.name}' transitioned to OPEN",
            provider_name=self.name,
            circuit_breaker_state=self.state.value,
            previous_state=old_state.value,
            failure_count=self.stats.failure_count,
            failure_threshold=self.config.failure_threshold
        )
    
    async def _transition_to_half_open(self):
        """Transition circuit breaker to HALF_OPEN state."""
        old_state = self.state
        self.state = CircuitBreakerState.HALF_OPEN
        self.stats.state_change_time = time.time()
        self.stats.reset_counts()
        
        # Update metrics
        self.metrics.set_circuit_breaker_state("sizecomparator", self.name, self.state)
        
        # Log state change
        self.logger.warning(
            f"Circuit breaker '{self.name}' transitioned to HALF_OPEN",
            provider_name=self.name,
            circuit_breaker_state=self.state.value,
            previous_state=old_state.value,
            timeout_seconds=self.config.timeout_seconds
        )
    
    async def _transition_to_closed(self):
        """Transition circuit breaker to CLOSED state."""
        old_state = self.state
        self.state = CircuitBreakerState.CLOSED
        self.stats.state_change_time = time.time()
        self.stats.reset_counts()
        
        # Update metrics
        self.metrics.set_circuit_breaker_state("sizecomparator", self.name, self.state)
        
        # Log state change
        self.logger.info(
            f"Circuit breaker '{self.name}' transitioned to CLOSED",
            provider_name=self.name,
            circuit_breaker_state=self.state.value,
            previous_state=old_state.value,
            success_count=self.stats.success_count,
            success_threshold=self.config.success_threshold
        )
    
    def _log_call_blocked(self):
        """Log when a call is blocked by circuit breaker."""
        self.logger.warning(
            f"Circuit breaker '{self.name}' blocked call",
            provider_name=self.name,
            circuit_breaker_state=self.state.value,
            failure_count=self.stats.failure_count,
            half_open_calls=self.stats.half_open_calls
        )
    
    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        return self.state
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            'state': self.state.value,
            'failure_count': self.stats.failure_count,
            'success_count': self.stats.success_count,
            'total_calls': self.stats.total_calls,
            'total_failures': self.stats.total_failures,
            'total_successes': self.stats.total_successes,
            'failure_rate': self.stats.get_failure_rate(),
            'success_rate': self.stats.get_success_rate(),
            'last_failure_time': self.stats.last_failure_time,
            'last_success_time': self.stats.last_success_time,
            'state_change_time': self.stats.state_change_time,
            'half_open_calls': self.stats.half_open_calls,
            'config': {
                'failure_threshold': self.config.failure_threshold,
                'success_threshold': self.config.success_threshold,
                'timeout_seconds': self.config.timeout_seconds,
                'half_open_max_calls': self.config.half_open_max_calls
            }
        }
    
    def is_call_permitted(self) -> bool:
        """Check if calls are currently permitted."""
        if self.state == CircuitBreakerState.OPEN:
            # Check if timeout has passed
            if (time.time() - self.stats.state_change_time) >= self.config.timeout_seconds:
                return True  # Would transition to HALF_OPEN
            return False
        
        if self.state == CircuitBreakerState.HALF_OPEN:
            return self.stats.half_open_calls < self.config.half_open_max_calls
        
        return True  # CLOSED state
    
    async def reset(self):
        """Reset circuit breaker to CLOSED state."""
        async with self._lock:
            old_state = self.state
            self.state = CircuitBreakerState.CLOSED
            self.stats = CircuitBreakerStats()
            
            # Update metrics
            self.metrics.update_circuit_breaker_state(self.name, self.state)
            
            # Log reset
            self.logger.info(
                f"Circuit breaker '{self.name}' manually reset",
                provider_name=self.name,
                circuit_breaker_state=self.state.value,
                previous_state=old_state.value
            )


class CircuitBreakerManager:
    """
    Manager for multiple circuit breakers.
    
    Provides centralized management and monitoring of all circuit breakers
    in the system, with integration to ERROR_MONITORING_SPEC alerting.
    """
    
    def __init__(self, logger=None, metrics=None):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.logger = logger or get_logger()
        self.metrics = metrics or get_metrics()
    
    def register_circuit_breaker(
        self, 
        name: str, 
        config: CircuitBreakerConfig
    ) -> CircuitBreaker:
        """Register a new circuit breaker."""
        if name in self.circuit_breakers:
            raise ValueError(f"Circuit breaker '{name}' already registered")
        
        circuit_breaker = CircuitBreaker(
            name=name,
            config=config,
            logger=self.logger,
            metrics=self.metrics
        )
        
        self.circuit_breakers[name] = circuit_breaker
        
        self.logger.info(
            f"Registered circuit breaker '{name}'",
            provider_name=name,
            failure_threshold=config.failure_threshold,
            success_threshold=config.success_threshold,
            timeout_seconds=config.timeout_seconds
        )
        
        return circuit_breaker
    
    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self.circuit_breakers.get(name)
    
    def get_all_states(self) -> Dict[str, CircuitBreakerState]:
        """Get states of all circuit breakers."""
        return {
            name: cb.get_state() 
            for name, cb in self.circuit_breakers.items()
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        return {
            name: cb.get_stats() 
            for name, cb in self.circuit_breakers.items()
        }
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get health summary for all circuit breakers."""
        states = self.get_all_states()
        stats = self.get_all_stats()
        
        open_count = sum(1 for state in states.values() if state == CircuitBreakerState.OPEN)
        half_open_count = sum(1 for state in states.values() if state == CircuitBreakerState.HALF_OPEN)
        closed_count = sum(1 for state in states.values() if state == CircuitBreakerState.CLOSED)
        
        # Calculate overall health
        total_failures = sum(stat['total_failures'] for stat in stats.values())
        total_calls = sum(stat['total_calls'] for stat in stats.values())
        overall_failure_rate = (total_failures / total_calls * 100) if total_calls > 0 else 0
        
        return {
            'total_circuit_breakers': len(self.circuit_breakers),
            'open_count': open_count,
            'half_open_count': half_open_count,
            'closed_count': closed_count,
            'overall_failure_rate': overall_failure_rate,
            'overall_health': 'healthy' if open_count == 0 else 'degraded' if half_open_count > 0 else 'unhealthy',
            'states': states,
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
    
    async def reset_all(self):
        """Reset all circuit breakers."""
        for name, cb in self.circuit_breakers.items():
            await cb.reset()
        
        self.logger.info("All circuit breakers reset")
    
    async def health_check(self) -> bool:
        """Perform health check on all circuit breakers."""
        states = self.get_all_states()
        
        # Consider system healthy if no circuit breakers are OPEN
        open_breakers = [name for name, state in states.items() if state == CircuitBreakerState.OPEN]
        
        if open_breakers:
            self.logger.warning(
                f"Circuit breakers in OPEN state: {open_breakers}",
                open_circuit_breakers=open_breakers
            )
            return False
        
        return True


# Decorator for applying circuit breaker to functions
def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    success_threshold: int = 2,
    timeout_seconds: int = 60,
    expected_exception: type = Exception
):
    """
    Decorator to apply circuit breaker to a function.
    
    Args:
        name: Circuit breaker name
        failure_threshold: Failures before opening
        success_threshold: Successes needed to close
        timeout_seconds: Timeout before trying half-open
        expected_exception: Exception type that triggers breaker
    """
    def decorator(func):
        # Create circuit breaker configuration
        config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            timeout_seconds=timeout_seconds,
            expected_exception=expected_exception
        )
        
        # Create circuit breaker
        cb = CircuitBreaker(name, config)
        
        async def async_wrapper(*args, **kwargs):
            return await cb.call(func, *args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(cb.call(func, *args, **kwargs))
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Default configurations for different services
DEFAULT_AI_PROVIDER_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,  # AI_PROVIDER_SPEC default
    success_threshold=2,  # AI_PROVIDER_SPEC default
    timeout_seconds=60,   # AI_PROVIDER_SPEC default
    half_open_max_calls=3,
    expected_exception=AIProviderException
)

DEFAULT_CACHE_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    success_threshold=2,
    timeout_seconds=30,
    half_open_max_calls=2,
    expected_exception=Exception
)

DEFAULT_EXTERNAL_API_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    success_threshold=3,
    timeout_seconds=60,
    half_open_max_calls=3,
    expected_exception=Exception
)