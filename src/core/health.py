"""
Health check system for DEPLOYMENT_OPS_SPEC compliance.

Provides /health, /ready, and /metrics endpoints with comprehensive
monitoring integration and dependency checking.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable
from pydantic import BaseModel, Field

from .monitoring import get_metrics, get_logger, CircuitBreakerState
from .circuit_breaker import CircuitBreakerManager
from .exceptions import ServiceUnavailableException


class HealthResponse(BaseModel):
    """Basic health response for load balancers (DEPLOYMENT_OPS_SPEC)."""
    status: str = Field(..., pattern="^(healthy|unhealthy)$")
    timestamp: datetime
    version: str
    service: str = "sizecomparator"


class ReadinessResponse(BaseModel):
    """Readiness response with dependency checks (DEPLOYMENT_OPS_SPEC)."""
    ready: bool
    checks: Dict[str, bool]
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None


class DependencyCheck:
    """Base class for dependency health checks."""
    
    def __init__(self, name: str, timeout_seconds: float = 5.0):
        self.name = name
        self.timeout_seconds = timeout_seconds
        self.last_check_time: Optional[float] = None
        self.last_result: Optional[bool] = None
        self.cache_ttl = 30  # Cache results for 30 seconds
    
    async def check(self) -> bool:
        """Perform health check with caching."""
        now = time.time()
        
        # Use cached result if available and fresh
        if (self.last_check_time and 
            self.last_result is not None and
            (now - self.last_check_time) < self.cache_ttl):
            return self.last_result
        
        try:
            # Perform check with timeout
            result = await asyncio.wait_for(
                self._perform_check(), 
                timeout=self.timeout_seconds
            )
            self.last_result = result
            self.last_check_time = now
            return result
            
        except asyncio.TimeoutError:
            self.last_result = False
            self.last_check_time = now
            return False
        except Exception:
            self.last_result = False
            self.last_check_time = now
            return False
    
    async def _perform_check(self) -> bool:
        """Override this method to implement specific health check."""
        raise NotImplementedError


class AIProviderHealthCheck(DependencyCheck):
    """Health check for AI provider connectivity."""
    
    def __init__(
        self, 
        name: str,
        circuit_breaker_manager: CircuitBreakerManager,
        provider_names: List[str],
        timeout_seconds: float = 10.0
    ):
        super().__init__(name, timeout_seconds)
        self.circuit_breaker_manager = circuit_breaker_manager
        self.provider_names = provider_names
    
    async def _perform_check(self) -> bool:
        """Check AI provider health via circuit breaker states."""
        if not self.provider_names:
            return True
        
        states = self.circuit_breaker_manager.get_all_states()
        
        # Consider healthy if at least one provider is not OPEN
        healthy_providers = 0
        for provider_name in self.provider_names:
            state = states.get(provider_name, CircuitBreakerState.CLOSED)
            if state != CircuitBreakerState.OPEN:
                healthy_providers += 1
        
        # Need at least one healthy provider
        return healthy_providers > 0


class CacheHealthCheck(DependencyCheck):
    """Health check for cache service connectivity."""
    
    def __init__(
        self,
        name: str,
        cache_client: Any,
        timeout_seconds: float = 5.0
    ):
        super().__init__(name, timeout_seconds)
        self.cache_client = cache_client
    
    async def _perform_check(self) -> bool:
        """Check cache connectivity with ping."""
        try:
            if hasattr(self.cache_client, 'ping'):
                if asyncio.iscoroutinefunction(self.cache_client.ping):
                    result = await self.cache_client.ping()
                else:
                    result = self.cache_client.ping()
                return bool(result)
            
            # Fallback: try a simple get operation
            if hasattr(self.cache_client, 'get'):
                if asyncio.iscoroutinefunction(self.cache_client.get):
                    await self.cache_client.get('__health_check__')
                else:
                    self.cache_client.get('__health_check__')
                return True
            
            return True  # No way to check, assume healthy
            
        except Exception:
            return False


class ConfigurationHealthCheck(DependencyCheck):
    """Health check for configuration validity."""
    
    def __init__(
        self,
        name: str,
        config_service: Any,
        required_configs: List[str],
        timeout_seconds: float = 2.0
    ):
        super().__init__(name, timeout_seconds)
        self.config_service = config_service
        self.required_configs = required_configs
    
    async def _perform_check(self) -> bool:
        """Check configuration validity."""
        try:
            # Check if config service is accessible
            if not hasattr(self.config_service, 'get'):
                return False
            
            # Check required configurations
            for config_path in self.required_configs:
                try:
                    value = self.config_service.get(config_path)
                    if value is None:
                        return False
                except Exception:
                    return False
            
            return True
            
        except Exception:
            return False


class DatabaseHealthCheck(DependencyCheck):
    """Health check for database connectivity."""
    
    def __init__(
        self,
        name: str,
        database_client: Any,
        timeout_seconds: float = 5.0
    ):
        super().__init__(name, timeout_seconds)
        self.database_client = database_client
    
    async def _perform_check(self) -> bool:
        """Check database connectivity."""
        try:
            # Try to execute a simple query
            if hasattr(self.database_client, 'execute'):
                if asyncio.iscoroutinefunction(self.database_client.execute):
                    await self.database_client.execute('SELECT 1')
                else:
                    self.database_client.execute('SELECT 1')
                return True
            
            # For connection pools
            if hasattr(self.database_client, 'ping'):
                if asyncio.iscoroutinefunction(self.database_client.ping):
                    result = await self.database_client.ping()
                else:
                    result = self.database_client.ping()
                return bool(result)
            
            return True  # Assume healthy if no way to check
            
        except Exception:
            return False


class ExternalServiceHealthCheck(DependencyCheck):
    """Health check for external service connectivity."""
    
    def __init__(
        self,
        name: str,
        health_url: str,
        http_client: Any,
        timeout_seconds: float = 10.0
    ):
        super().__init__(name, timeout_seconds)
        self.health_url = health_url
        self.http_client = http_client
    
    async def _perform_check(self) -> bool:
        """Check external service health endpoint."""
        try:
            if asyncio.iscoroutinefunction(getattr(self.http_client, 'get', None)):
                response = await self.http_client.get(self.health_url)
            else:
                response = self.http_client.get(self.health_url)
            
            return 200 <= response.status_code < 300
            
        except Exception:
            return False


class HealthCheckService:
    """
    Main health check service for DEPLOYMENT_OPS_SPEC compliance.
    
    Provides /health, /ready endpoints with comprehensive dependency checking
    and monitoring integration.
    """
    
    def __init__(
        self,
        version: str = "1.0.0",
        service_name: str = "sizecomparator",
        circuit_breaker_manager: Optional[CircuitBreakerManager] = None,
        logger=None,
        metrics=None
    ):
        self.version = version
        self.service_name = service_name
        self.circuit_breaker_manager = circuit_breaker_manager
        self.logger = logger or get_logger()
        self.metrics = metrics or get_metrics()
        self.dependencies: Dict[str, DependencyCheck] = {}
        self.startup_time = time.time()
        
        # Track health check metrics
        self.health_check_count = 0
        self.readiness_check_count = 0
    
    def register_dependency(self, dependency: DependencyCheck):
        """Register a dependency health check."""
        self.dependencies[dependency.name] = dependency
        
        self.logger.info(
            f"Registered health check dependency: {dependency.name}",
            dependency_name=dependency.name,
            timeout_seconds=dependency.timeout_seconds
        )
    
    def register_ai_provider_check(
        self,
        provider_names: List[str],
        timeout_seconds: float = 10.0
    ):
        """Register AI provider health check."""
        if self.circuit_breaker_manager:
            check = AIProviderHealthCheck(
                name="ai_providers",
                circuit_breaker_manager=self.circuit_breaker_manager,
                provider_names=provider_names,
                timeout_seconds=timeout_seconds
            )
            self.register_dependency(check)
    
    def register_cache_check(
        self,
        cache_client: Any,
        timeout_seconds: float = 5.0
    ):
        """Register cache health check."""
        check = CacheHealthCheck(
            name="cache",
            cache_client=cache_client,
            timeout_seconds=timeout_seconds
        )
        self.register_dependency(check)
    
    def register_configuration_check(
        self,
        config_service: Any,
        required_configs: List[str],
        timeout_seconds: float = 2.0
    ):
        """Register configuration health check."""
        check = ConfigurationHealthCheck(
            name="configuration",
            config_service=config_service,
            required_configs=required_configs,
            timeout_seconds=timeout_seconds
        )
        self.register_dependency(check)
    
    def register_database_check(
        self,
        database_client: Any,
        timeout_seconds: float = 5.0
    ):
        """Register database health check."""
        check = DatabaseHealthCheck(
            name="database",
            database_client=database_client,
            timeout_seconds=timeout_seconds
        )
        self.register_dependency(check)
    
    def register_external_service_check(
        self,
        name: str,
        health_url: str,
        http_client: Any,
        timeout_seconds: float = 10.0
    ):
        """Register external service health check."""
        check = ExternalServiceHealthCheck(
            name=name,
            health_url=health_url,
            http_client=http_client,
            timeout_seconds=timeout_seconds
        )
        self.register_dependency(check)
    
    async def health_check(self) -> HealthResponse:
        """
        Basic health check for liveness probe (DEPLOYMENT_OPS_SPEC).
        
        This should be fast and only check if the service is alive,
        not its dependencies.
        """
        self.health_check_count += 1
        
        # Basic service health - just check if we can respond
        try:
            status = "healthy"
            
            # Update health metrics
            self.metrics.update_health_status(self.service_name, True)
            
            self.logger.debug(
                "Health check passed",
                status=status,
                check_count=self.health_check_count
            )
            
            return HealthResponse(
                status=status,
                timestamp=datetime.now(timezone.utc),
                version=self.version,
                service=self.service_name
            )
            
        except Exception as e:
            status = "unhealthy"
            
            # Update health metrics
            self.metrics.update_health_status(self.service_name, False)
            
            self.logger.error(
                "Health check failed",
                status=status,
                error=str(e),
                check_count=self.health_check_count
            )
            
            return HealthResponse(
                status=status,
                timestamp=datetime.now(timezone.utc),
                version=self.version,
                service=self.service_name
            )
    
    async def readiness_check(self) -> ReadinessResponse:
        """
        Comprehensive readiness check for readiness probe (DEPLOYMENT_OPS_SPEC).
        
        Checks all dependencies and service readiness.
        """
        self.readiness_check_count += 1
        start_time = time.time()
        
        checks = {}
        overall_ready = True
        
        # Perform all dependency checks
        check_tasks = [
            self._perform_dependency_check(name, dep) 
            for name, dep in self.dependencies.items()
        ]
        
        if check_tasks:
            check_results = await asyncio.gather(*check_tasks, return_exceptions=True)
            
            for i, (name, _) in enumerate(self.dependencies.items()):
                result = check_results[i]
                if isinstance(result, Exception):
                    checks[name] = False
                    overall_ready = False
                else:
                    checks[name] = result
                    if not result:
                        overall_ready = False
        
        # Update health metrics for each dependency
        for name, is_healthy in checks.items():
            self.metrics.update_health_status(f"dependency_{name}", is_healthy)
        
        # Get additional details
        details = await self._get_readiness_details()
        
        duration = time.time() - start_time
        
        self.logger.info(
            "Readiness check completed",
            ready=overall_ready,
            checks=checks,
            duration_seconds=duration,
            check_count=self.readiness_check_count
        )
        
        return ReadinessResponse(
            ready=overall_ready,
            checks=checks,
            timestamp=datetime.now(timezone.utc),
            details=details
        )
    
    async def _perform_dependency_check(self, name: str, dependency: DependencyCheck) -> bool:
        """Perform individual dependency check."""
        try:
            result = await dependency.check()
            
            self.logger.debug(
                f"Dependency check completed: {name}",
                dependency_name=name,
                result=result
            )
            
            return result
            
        except Exception as e:
            self.logger.warning(
                f"Dependency check failed: {name}",
                dependency_name=name,
                error=str(e)
            )
            return False
    
    async def _get_readiness_details(self) -> Dict[str, Any]:
        """Get additional readiness details for debugging."""
        details = {
            'uptime_seconds': time.time() - self.startup_time,
            'health_check_count': self.health_check_count,
            'readiness_check_count': self.readiness_check_count,
            'registered_dependencies': list(self.dependencies.keys()),
            'service_name': self.service_name,
            'version': self.version
        }
        
        # Add circuit breaker information if available
        if self.circuit_breaker_manager:
            details['circuit_breakers'] = self.circuit_breaker_manager.get_health_summary()
        
        # Add memory usage if psutil is available
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            details['memory_usage'] = {
                'rss_mb': memory_info.rss / 1024 / 1024,
                'vms_mb': memory_info.vms / 1024 / 1024,
                'percentage': process.memory_percent()
            }
        except ImportError:
            pass
        
        return details
    
    def get_metrics_text(self) -> str:
        """Get Prometheus metrics in text format."""
        return self.metrics.get_metrics_text()
    
    async def startup_check(self) -> bool:
        """
        Perform startup health check to verify all systems are ready.
        
        Should be called during application startup to ensure all
        dependencies are available before accepting traffic.
        """
        self.logger.info("Performing startup health check")
        
        readiness = await self.readiness_check()
        
        if readiness.ready:
            self.logger.info(
                "Startup health check passed - service ready",
                checks=readiness.checks
            )
            return True
        else:
            failed_checks = [
                name for name, result in readiness.checks.items() 
                if not result
            ]
            
            self.logger.error(
                "Startup health check failed - service not ready",
                failed_checks=failed_checks,
                checks=readiness.checks
            )
            return False
    
    async def shutdown_check(self) -> bool:
        """
        Perform graceful shutdown check.
        
        Should be called during application shutdown to verify
        resources are properly cleaned up.
        """
        self.logger.info("Performing shutdown health check")
        
        # Give time for in-flight requests to complete
        await asyncio.sleep(1)
        
        # Check if any critical resources need cleanup
        # This could include database connections, cache connections, etc.
        
        self.logger.info("Shutdown health check completed")
        return True