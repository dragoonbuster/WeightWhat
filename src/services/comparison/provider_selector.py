"""
AI Provider Selection Logic

Intelligent selection of AI providers based on multiple criteria including
availability, cost, capability, performance, and weight context.
"""

import asyncio
import hashlib
import logging
import random
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Protocol

from ...core.simple_config import SimpleConfig
from ...models.providers import AIProvider
from .types import WeightCategory, WeightContext

logger = logging.getLogger(__name__)


class ProviderScore:
    """Multi-dimensional score for provider selection"""
    def __init__(
        self,
        provider: AIProvider,
        total_score: float,
        availability: float,
        cost: float,
        capability: float,
        performance: float
    ):
        self.provider = provider
        self.total_score = total_score
        self.availability = availability
        self.cost = cost
        self.capability = capability
        self.performance = performance


class ProviderMetrics:
    """Metrics tracking for provider performance"""
    def __init__(self):
        self.total_uses = 0
        self.successful_uses = 0
        self.average_response_time = 0.0
        self.average_quality = 0.0
        self.last_used = None
        self.circuit_breaker_trips = 0


class NoProvidersAvailableError(Exception):
    """Raised when no providers are available"""
    pass


class AllProvidersFailed(Exception):
    """Raised when all providers in fallback chain fail"""
    def __init__(self, message: str, attempted: Set[str]):
        super().__init__(message)
        self.attempted = attempted


class IAIProviderFactory(Protocol):
    """AI Provider factory interface"""
    async def get_provider(self, name: str) -> Any:
        """Get AI provider by name"""
        ...
        
    async def get_available_providers(self) -> List[AIProvider]:
        """Get list of available providers"""
        ...


class ProviderSelector:
    """Intelligent AI provider selection based on multiple criteria"""
    
    def __init__(self, provider_factory: IAIProviderFactory, config: SimpleConfig):
        self._provider_factory = provider_factory
        self._config = config
        self._selection_history = deque(maxlen=1000)
        self._provider_metrics = defaultdict(ProviderMetrics)
        
        # Load configuration
        self._load_configuration()
        
        # Initialize provider specialization map
        self._specialization_map = self._initialize_specialization_map()
        
        # A/B testing
        self._ab_test_config = self._config.get_section("ab_tests", {})
        
    def _load_configuration(self):
        """Load provider selection configuration"""
        self._selection_strategy = self._config.get_section(
            "comparison_service.provider_selection.strategy",
            "cost_optimized"
        )
        
        self._fallback_chain = self._config.get_section(
            "comparison_service.provider_selection.fallback_chain",
            ["openai", "anthropic", "xai"]
        )
        
        self._cost_threshold = self._config.get_section(
            "comparison_service.provider_selection.cost_threshold",
            0.01
        )
        
        self._enable_load_balancing = self._config.get_section(
            "comparison_service.provider_selection.enable_load_balancing",
            True
        )
        
    def _initialize_specialization_map(self) -> Dict[WeightCategory, Dict[str, str]]:
        """Initialize provider specialization mapping"""
        return {
            WeightCategory.MICROSCOPIC: {
                "primary": "openai",      # Good at scientific/technical
                "secondary": "anthropic"
            },
            WeightCategory.VERY_LIGHT: {
                "primary": "anthropic",   # Creative comparisons
                "secondary": "openai"
            },
            WeightCategory.LIGHT: {
                "primary": "xai",         # Cost-effective for common weights
                "secondary": "openai"
            },
            WeightCategory.MEDIUM: {
                "primary": "xai",
                "secondary": "anthropic"
            },
            WeightCategory.HEAVY: {
                "primary": "anthropic",   # Good with vehicles/animals
                "secondary": "openai"
            },
            WeightCategory.MASSIVE: {
                "primary": "openai",      # Technical accuracy for large scale
                "secondary": "anthropic"
            }
        }
        
    async def select_provider(
        self,
        preferred_provider: Optional[AIProvider],
        weight_context: WeightContext,
        comparison_style: str
    ) -> AIProvider:
        """Select optimal provider based on criteria"""
        
        # Check A/B testing
        ab_test_provider = self._check_ab_testing()
        if ab_test_provider:
            return AIProvider(ab_test_provider)
        
        # Check if user has explicit preference
        if preferred_provider and await self._is_provider_available(preferred_provider):
            return preferred_provider
        
        # Get all available providers
        available_providers = await self._get_available_providers()
        if not available_providers:
            raise NoProvidersAvailableError("All AI providers are currently unavailable")
        
        # Score providers based on criteria
        provider_scores = []
        for provider in available_providers:
            score = await self._calculate_provider_score(
                provider, weight_context, comparison_style
            )
            provider_scores.append(score)
            
        # Sort by total score (descending)
        provider_scores.sort(key=lambda x: x.total_score, reverse=True)
        
        # Apply selection strategy
        selected = self._apply_selection_strategy(provider_scores)
        
        # Track selection for analytics
        self._track_selection(selected, weight_context, comparison_style)
        
        return selected
        
    def _check_ab_testing(self) -> Optional[str]:
        """Check if A/B testing should override selection"""
        for test_name, test_config in self._ab_test_config.items():
            if not test_config.get("enabled", False):
                continue
                
            traffic_percentage = test_config.get("traffic_percentage", 0)
            if random.random() * 100 <= traffic_percentage:
                return test_config.get("test_provider")
                
        return None
        
    async def _is_provider_available(self, provider: AIProvider) -> bool:
        """Check if specific provider is available"""
        try:
            available = await self._provider_factory.get_available_providers()
            return provider in available
        except Exception as e:
            logger.warning(f"Failed to check provider availability: {e}")
            return False
            
    async def _get_available_providers(self) -> List[AIProvider]:
        """Get list of available providers"""
        try:
            return await self._provider_factory.get_available_providers()
        except Exception as e:
            logger.error(f"Failed to get available providers: {e}")
            return []
            
    async def _calculate_provider_score(
        self,
        provider: AIProvider,
        weight_context: WeightContext,
        comparison_style: str
    ) -> ProviderScore:
        """Calculate multi-dimensional score for provider"""
        
        # Base scores (0.0 to 1.0)
        availability_score = await self._get_availability_score(provider)
        cost_score = self._get_cost_score(provider, weight_context)
        capability_score = self._get_capability_score(provider, comparison_style)
        performance_score = self._get_performance_score(provider)
        
        # Determine weights based on context
        weights = self._get_scoring_weights(comparison_style, weight_context)
        
        # Calculate weighted total score
        total_score = (
            availability_score * weights["availability"] +
            cost_score * weights["cost"] +
            capability_score * weights["capability"] +
            performance_score * weights["performance"]
        )
        
        return ProviderScore(
            provider=provider,
            total_score=total_score,
            availability=availability_score,
            cost=cost_score,
            capability=capability_score,
            performance=performance_score
        )
        
    def _get_scoring_weights(
        self,
        comparison_style: str,
        weight_context: WeightContext
    ) -> Dict[str, float]:
        """Get scoring weights based on context"""
        
        if comparison_style == "creative":
            return {
                "availability": 0.2,
                "cost": 0.1,
                "capability": 0.5,
                "performance": 0.2
            }
        elif weight_context.category == WeightCategory.MICROSCOPIC:
            # Technical accuracy important
            return {
                "availability": 0.2,
                "cost": 0.1,
                "capability": 0.4,
                "performance": 0.3
            }
        else:  # Default balanced weights
            return {
                "availability": 0.3,
                "cost": 0.3,
                "capability": 0.2,
                "performance": 0.2
            }
            
    async def _get_availability_score(self, provider: AIProvider) -> float:
        """Calculate availability score for provider"""
        
        metrics = self._provider_metrics[provider.value]
        
        # Check recent success rate
        if metrics.total_uses == 0:
            return 0.8  # New provider gets benefit of doubt
            
        success_rate = metrics.successful_uses / metrics.total_uses
        
        # Check circuit breaker status
        if metrics.circuit_breaker_trips > 5:
            success_rate *= 0.5  # Penalize frequent circuit breaker trips
            
        # Recent usage penalty (avoid overloading)
        if metrics.last_used:
            minutes_since_use = (datetime.utcnow() - metrics.last_used).total_seconds() / 60
            if minutes_since_use < 1:
                success_rate *= 0.8  # Small penalty for very recent use
                
        return min(1.0, success_rate)
        
    def _get_cost_score(self, provider: AIProvider, weight_context: WeightContext) -> float:
        """Calculate cost effectiveness score"""
        
        # Base cost per request (simplified)
        base_costs = {
            "openai": 0.02,
            "anthropic": 0.015,
            "xai": 0.005
        }
        
        cost = base_costs.get(provider.value, 0.02)
        
        # Adjust for weight category complexity
        complexity_multipliers = {
            WeightCategory.MICROSCOPIC: 1.5,  # More complex scientific comparisons
            WeightCategory.VERY_LIGHT: 1.0,
            WeightCategory.LIGHT: 0.8,        # Common comparisons
            WeightCategory.MEDIUM: 0.8,
            WeightCategory.HEAVY: 1.2,        # More specialized
            WeightCategory.MASSIVE: 1.5
        }
        
        adjusted_cost = cost * complexity_multipliers.get(weight_context.category, 1.0)
        
        # Convert to score (lower cost = higher score)
        max_cost = 0.1
        cost_score = max(0, (max_cost - adjusted_cost) / max_cost)
        
        return cost_score
        
    def _get_capability_score(self, provider: AIProvider, comparison_style: str) -> float:
        """Calculate capability score based on provider strengths"""
        
        # Provider capability matrix
        capabilities = {
            "openai": {
                "default": 0.9,
                "creative": 0.8,
                "technical": 0.95,
                "educational": 0.9
            },
            "anthropic": {
                "default": 0.85,
                "creative": 0.95,
                "technical": 0.8,
                "educational": 0.9
            },
            "xai": {
                "default": 0.8,
                "creative": 0.7,
                "technical": 0.75,
                "educational": 0.75
            }
        }
        
        provider_caps = capabilities.get(provider.value, {})
        return provider_caps.get(comparison_style, 0.7)
        
    def _get_performance_score(self, provider: AIProvider) -> float:
        """Calculate performance score based on response times"""
        
        metrics = self._provider_metrics[provider.value]
        
        if metrics.total_uses == 0:
            return 0.8  # Default for new providers
            
        # Target response time: 1000ms
        target_time = 1000.0
        avg_time = metrics.average_response_time
        
        if avg_time <= target_time:
            return 1.0
        elif avg_time <= target_time * 2:
            # Linear degradation up to 2x target
            return 1.0 - (avg_time - target_time) / target_time * 0.5
        else:
            # Significant penalty for very slow responses
            return 0.3
            
    def _apply_selection_strategy(self, provider_scores: List[ProviderScore]) -> AIProvider:
        """Apply configured selection strategy"""
        
        if not provider_scores:
            raise NoProvidersAvailableError("No providers scored")
            
        if self._selection_strategy == "highest_score":
            return provider_scores[0].provider
            
        elif self._selection_strategy == "cost_optimized":
            # Filter providers above cost threshold
            cost_efficient = [
                score for score in provider_scores 
                if score.cost >= 0.7  # Only consider cost-efficient providers
            ]
            if cost_efficient:
                return cost_efficient[0].provider
            else:
                return provider_scores[0].provider  # Fallback to best overall
                
        elif self._selection_strategy == "round_robin":
            return self._round_robin_selection(provider_scores)
            
        elif self._selection_strategy == "weighted_random":
            return self._weighted_random_selection(provider_scores)
            
        else:
            # Default to highest score
            return provider_scores[0].provider
            
    def _round_robin_selection(self, provider_scores: List[ProviderScore]) -> AIProvider:
        """Round-robin selection among top providers"""
        
        # Get top 3 providers
        top_providers = provider_scores[:3]
        
        # Simple round-robin based on selection count
        selection_counts = {
            score.provider: len([h for h in self._selection_history if h == score.provider])
            for score in top_providers
        }
        
        # Select provider with least recent selections
        selected = min(top_providers, key=lambda s: selection_counts[s.provider])
        return selected.provider
        
    def _weighted_random_selection(self, provider_scores: List[ProviderScore]) -> AIProvider:
        """Weighted random selection based on scores"""
        
        weights = [score.total_score for score in provider_scores]
        
        # Ensure all weights are positive
        min_weight = min(weights)
        if min_weight <= 0:
            weights = [w - min_weight + 0.1 for w in weights]
            
        selected_score = random.choices(provider_scores, weights=weights)[0]
        return selected_score.provider
        
    def _track_selection(
        self,
        selected_provider: AIProvider,
        weight_context: WeightContext,
        comparison_style: str
    ):
        """Track provider selection for analytics"""
        
        selection_record = {
            "provider": selected_provider,
            "category": weight_context.category,
            "style": comparison_style,
            "timestamp": datetime.utcnow()
        }
        
        self._selection_history.append(selection_record)
        
        # Update metrics
        metrics = self._provider_metrics[selected_provider.value]
        metrics.last_used = datetime.utcnow()
        
        logger.debug(f"Selected provider {selected_provider} for {weight_context.category} comparison")
        
    def track_provider_result(
        self,
        provider: AIProvider,
        success: bool,
        response_time_ms: float,
        quality_score: Optional[float] = None
    ):
        """Track provider performance results"""
        
        metrics = self._provider_metrics[provider.value]
        metrics.total_uses += 1
        
        if success:
            metrics.successful_uses += 1
            
        # Update rolling average response time
        if metrics.average_response_time == 0:
            metrics.average_response_time = response_time_ms
        else:
            # Simple exponential moving average
            alpha = 0.1
            metrics.average_response_time = (
                alpha * response_time_ms + 
                (1 - alpha) * metrics.average_response_time
            )
            
        # Update quality score
        if quality_score is not None:
            if metrics.average_quality == 0:
                metrics.average_quality = quality_score
            else:
                metrics.average_quality = (
                    alpha * quality_score + 
                    (1 - alpha) * metrics.average_quality
                )
                
    def get_provider_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get provider performance statistics"""
        
        stats = {}
        for provider_name, metrics in self._provider_metrics.items():
            success_rate = (
                metrics.successful_uses / metrics.total_uses 
                if metrics.total_uses > 0 else 0
            )
            
            stats[provider_name] = {
                "total_uses": metrics.total_uses,
                "success_rate": success_rate,
                "average_response_time_ms": metrics.average_response_time,
                "average_quality": metrics.average_quality,
                "circuit_breaker_trips": metrics.circuit_breaker_trips,
                "last_used": metrics.last_used.isoformat() if metrics.last_used else None
            }
            
        return stats
        
    def get_specialization_recommendation(
        self,
        weight_category: WeightCategory
    ) -> Optional[str]:
        """Get specialized provider recommendation for weight category"""
        
        specialization = self._specialization_map.get(weight_category)
        if not specialization:
            return None
            
        # Return primary recommendation
        return specialization.get("primary")
        
    async def execute_with_fallback(
        self,
        primary_provider: AIProvider,
        operation_func,
        *args,
        **kwargs
    ) -> Tuple[Any, AIProvider]:
        """Execute operation with automatic fallback"""
        
        attempted_providers = set()
        last_error = None
        
        # Try primary provider first
        try:
            result = await operation_func(primary_provider, *args, **kwargs)
            return result, primary_provider
        except Exception as e:
            last_error = e
            attempted_providers.add(primary_provider.value)
            logger.warning(f"Primary provider {primary_provider} failed: {e}")
            
        # Try fallback chain
        for provider_name in self._fallback_chain:
            if provider_name in attempted_providers:
                continue
                
            try:
                provider = AIProvider(provider_name)
                if await self._is_provider_available(provider):
                    result = await operation_func(provider, *args, **kwargs)
                    return result, provider
            except Exception as e:
                last_error = e
                attempted_providers.add(provider_name)
                logger.warning(f"Fallback provider {provider_name} failed: {e}")
                
        raise AllProvidersFailed(
            f"All providers failed. Last error: {last_error}",
            attempted=attempted_providers
        )