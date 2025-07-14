"""
Provider factory for managing AI provider instances.

Implements registration, configuration, and lifecycle management for providers
with automatic failover and health monitoring.
"""

import asyncio
from typing import Dict, Type, Optional, List, Any
from datetime import datetime, timezone

from ..models.providers import (
    ProviderConfiguration, AIProviderRequest, AIProviderHealth,
    ProviderStatus, ProviderFallbackConfig, AIProvider
)
from ..models.responses import WeightComparisonResponse
from ..core.monitoring import get_logger, get_metrics
from ..core.exceptions import (
    ProviderNotFoundException, AIProviderException,
    ConfigurationException
)
from .base import AIProviderBase, ProviderCapabilities


class ProviderRegistry:
    """Registry for available provider implementations."""
    
    def __init__(self):
        self._providers: Dict[str, Type[AIProviderBase]] = {}
        self._capabilities: Dict[str, ProviderCapabilities] = {}
    
    def register(
        self,
        name: str,
        provider_class: Type[AIProviderBase],
        capabilities: ProviderCapabilities
    ):
        """Register a provider implementation."""
        if name in self._providers:
            raise ValueError(f"Provider {name} already registered")
        
        self._providers[name] = provider_class
        self._capabilities[name] = capabilities
    
    def get_provider_class(self, name: str) -> Type[AIProviderBase]:
        """Get provider class by name."""
        if name not in self._providers:
            raise ProviderNotFoundException(
                f"Provider {name} not registered",
                details={'available_providers': list(self._providers.keys())}
            )
        return self._providers[name]
    
    def get_capabilities(self, name: str) -> ProviderCapabilities:
        """Get provider capabilities by name."""
        if name not in self._capabilities:
            raise ProviderNotFoundException(
                f"Provider {name} not registered",
                details={'available_providers': list(self._providers.keys())}
            )
        return self._capabilities[name]
    
    def list_providers(self) -> List[str]:
        """List all registered provider names."""
        return list(self._providers.keys())


class ProviderFactory:
    """
    Factory for creating and managing AI provider instances.
    
    Handles provider lifecycle, configuration, health monitoring,
    and automatic failover as per AI_PROVIDER_SPEC.
    """
    
    def __init__(
        self,
        registry: Optional[ProviderRegistry] = None,
        logger: Optional[Any] = None,
        metrics: Optional[Any] = None
    ):
        self.registry = registry or ProviderRegistry()
        self.logger = logger or get_logger()
        self.metrics = metrics or get_metrics()
        
        # Active provider instances
        self._instances: Dict[str, AIProviderBase] = {}
        
        # Provider priority for failover
        self._provider_priority: List[str] = []
        
        # Fallback configuration
        self._fallback_config: Optional[ProviderFallbackConfig] = None
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()
    
    async def create_provider(
        self,
        config: ProviderConfiguration
    ) -> AIProviderBase:
        """Create a provider instance from configuration."""
        provider_class = self.registry.get_provider_class(config.provider_name)
        capabilities = self.registry.get_capabilities(config.provider_name)
        
        # Create provider instance
        provider = provider_class(
            config=config,
            capabilities=capabilities,
            logger=self.logger,
            metrics=self.metrics
        )
        
        # Initialize provider
        await provider.on_startup()
        
        # Store instance
        async with self._lock:
            self._instances[config.provider_name] = provider
            
            # Update priority list
            if config.enabled:
                self._update_priority_list()
        
        self.logger.info(
            f"Created provider instance: {config.provider_name}",
            provider_name=config.provider_name,
            priority=config.priority,
            enabled=config.enabled
        )
        
        return provider
    
    async def get_provider(self, name: str) -> AIProviderBase:
        """Get provider instance by name."""
        if name not in self._instances:
            raise ProviderNotFoundException(
                f"Provider instance {name} not found",
                details={'available_instances': list(self._instances.keys())}
            )
        return self._instances[name]
    
    async def get_primary_provider(self) -> AIProviderBase:
        """Get the highest priority healthy provider."""
        async with self._lock:
            for provider_name in self._provider_priority:
                provider = self._instances.get(provider_name)
                if provider:
                    health = provider.get_health_status()
                    if health.status != ProviderStatus.UNHEALTHY:
                        return provider
        
        raise AIProviderException(
            "No healthy providers available",
            details={'provider_states': await self.get_all_health_status()}
        )
    
    def configure_fallback(self, config: ProviderFallbackConfig):
        """Configure fallback behavior."""
        self._fallback_config = config
        self.logger.info(
            "Configured provider fallback",
            enabled=config.enabled,
            fallback_chain=config.fallback_chain,
            max_attempts=config.max_fallback_attempts
        )
    
    async def generate_comparison_with_fallback(
        self,
        request: AIProviderRequest
    ) -> WeightComparisonResponse:
        """
        Generate comparison with automatic fallback on failure.
        
        Tries providers in priority order until one succeeds or all fail.
        """
        if not self._fallback_config or not self._fallback_config.enabled:
            # No fallback configured, use primary provider
            provider = await self.get_primary_provider()
            return await provider.generate_comparison(request)
        
        errors = []
        attempted_providers = []
        
        # Try providers in fallback chain
        for i, provider_name in enumerate(self._fallback_config.fallback_chain):
            if i >= self._fallback_config.max_fallback_attempts:
                break
            
            try:
                provider = await self.get_provider(provider_name)
                
                # Check if provider is healthy enough to try
                health = provider.get_health_status()
                if health.status == ProviderStatus.UNHEALTHY:
                    self.logger.warning(
                        f"Skipping unhealthy provider {provider_name} in fallback chain",
                        provider_name=provider_name,
                        health_status=health.status
                    )
                    continue
                
                # Update request for retry tracking
                request.retry_count = i
                
                # Log fallback attempt
                if i > 0:
                    self.logger.info(
                        f"Attempting fallback to provider {provider_name}",
                        provider_name=provider_name,
                        attempt=i + 1,
                        previous_provider=attempted_providers[-1] if attempted_providers else None,
                        request_id=str(request.request_id)
                    )
                
                # Try the provider
                start_time = datetime.now(timezone.utc)
                response = await provider.generate_comparison(request)
                
                # Record successful fallback
                if i > 0:
                    self.metrics.record_provider_fallback(
                        original_provider=attempted_providers[0],
                        fallback_provider=provider_name,
                        attempt_number=i + 1,
                        success=True
                    )
                
                return response
                
            except Exception as e:
                errors.append({
                    'provider': provider_name,
                    'error': str(e),
                    'error_type': type(e).__name__
                })
                attempted_providers.append(provider_name)
                
                self.logger.error(
                    f"Provider {provider_name} failed",
                    provider_name=provider_name,
                    error=str(e),
                    error_type=type(e).__name__,
                    request_id=str(request.request_id)
                )
                
                # Record failed fallback
                if i > 0:
                    self.metrics.record_provider_fallback(
                        original_provider=attempted_providers[0],
                        fallback_provider=provider_name,
                        attempt_number=i + 1,
                        success=False
                    )
        
        # All providers failed
        raise AIProviderException(
            "All providers in fallback chain failed",
            details={
                'attempted_providers': attempted_providers,
                'errors': errors,
                'request_id': str(request.request_id)
            }
        )
    
    def _update_priority_list(self):
        """Update provider priority list based on configuration."""
        # Sort providers by priority (lower number = higher priority)
        sorted_providers = sorted(
            [
                (name, instance.config.priority)
                for name, instance in self._instances.items()
                if instance.config.enabled
            ],
            key=lambda x: x[1]
        )
        
        self._provider_priority = [name for name, _ in sorted_providers]
    
    async def get_all_health_status(self) -> Dict[str, AIProviderHealth]:
        """Get health status for all providers."""
        health_status = {}
        
        async with self._lock:
            for name, provider in self._instances.items():
                health_status[name] = provider.get_health_status()
        
        return health_status
    
    async def perform_health_checks(self) -> Dict[str, bool]:
        """Perform health checks on all providers."""
        results = {}
        
        async def check_provider(name: str, provider: AIProviderBase) -> tuple:
            try:
                result = await provider.health_check()
                return (name, result)
            except Exception as e:
                self.logger.error(
                    f"Health check failed for provider {name}",
                    provider_name=name,
                    error=str(e)
                )
                return (name, False)
        
        # Run health checks concurrently
        tasks = [
            check_provider(name, provider)
            for name, provider in self._instances.items()
        ]
        
        check_results = await asyncio.gather(*tasks)
        
        for name, result in check_results:
            results[name] = result
        
        return results
    
    async def shutdown_all(self):
        """Shutdown all provider instances."""
        async with self._lock:
            shutdown_tasks = [
                provider.shutdown()
                for provider in self._instances.values()
            ]
            
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)
            
            self._instances.clear()
            self._provider_priority.clear()
        
        self.logger.info("All providers shut down")
    
    def get_provider_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all providers."""
        metrics = {}
        
        for name, provider in self._instances.items():
            health = provider.get_health_status()
            metrics[name] = {
                'status': health.status,
                'success_rate': health.success_rate,
                'avg_response_time_ms': health.avg_response_time_ms,
                'requests_per_minute': health.requests_per_minute,
                'error_count': health.error_count,
                'circuit_breaker_state': health.circuit_breaker_state
            }
        
        return metrics


# Global factory instance
_factory: Optional[ProviderFactory] = None


def get_factory() -> ProviderFactory:
    """Get the global provider factory instance."""
    global _factory
    if _factory is None:
        _factory = ProviderFactory()
    return _factory


def register_provider(
    name: str,
    provider_class: Type[AIProviderBase],
    capabilities: ProviderCapabilities
):
    """Register a provider with the global factory."""
    factory = get_factory()
    factory.registry.register(name, provider_class, capabilities)


async def get_provider(name: str) -> AIProviderBase:
    """Get a provider instance from the global factory."""
    factory = get_factory()
    return await factory.get_provider(name)