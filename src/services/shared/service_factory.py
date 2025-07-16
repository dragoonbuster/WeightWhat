"""
Service Factory for Intelligent Comparison Service Selection

This factory provides intelligent routing to optimal comparison services based on:
- Weight category and complexity
- Timeout requirements
- Performance characteristics
- Environment configuration
- Service availability

The factory automatically selects the best service for each use case,
balancing accuracy, speed, and reliability.
"""

import os
import logging
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum
from dataclasses import dataclass
from decimal import Decimal

from src.models.mvp import MVPComparisonRequest, MVPComparisonResponse
from src.services.shared.interfaces import BaseComparisonService
from src.services.fast_validation_service import FastValidationService
from src.services.ai_validation_service import AIValidationService
from src.services.mvp_comparison import MVPComparisonService
from src.core.environment import EnvironmentManager, EnvironmentType
from src.core.simple_config import get_config

logger = logging.getLogger(__name__)


class ServiceType(str, Enum):
    """Available comparison service types"""
    BASIC = "basic"
    FAST_VALIDATION = "fast_validation"
    FULL_VALIDATION = "full_validation"
    COMPREHENSIVE = "comprehensive"


class PerformanceProfile(str, Enum):
    """Performance optimization profiles"""
    SPEED_OPTIMIZED = "speed_optimized"      # < 2 seconds, basic validation
    BALANCED = "balanced"                    # 2-5 seconds, moderate validation
    ACCURACY_OPTIMIZED = "accuracy_optimized"  # 5-10 seconds, full validation


@dataclass
class ServiceRequirements:
    """Requirements for service selection"""
    weight_kg: float
    timeout_ms: int
    accuracy_priority: bool = False
    speed_priority: bool = False
    user_context: Optional[Dict[str, Any]] = None
    performance_profile: PerformanceProfile = PerformanceProfile.BALANCED


@dataclass
class ServiceCapabilities:
    """Capabilities and characteristics of a comparison service"""
    service_type: ServiceType
    avg_response_time_ms: int
    accuracy_score: float  # 0.0 to 1.0
    supports_extreme_weights: bool
    supports_custom_styles: bool
    requires_ai_providers: bool
    fallback_available: bool
    resource_intensity: int  # 1-5 scale


class ComparisonServiceFactory:
    """Factory for creating and selecting optimal comparison services"""
    
    def __init__(self, env_manager: Optional[EnvironmentManager] = None):
        """Initialize factory with environment configuration"""
        self.env_manager = env_manager
        self.logger = logger
        
        # Service capability profiles
        self.service_capabilities = self._initialize_service_capabilities()
        
        # Performance tuning parameters from environment
        self.performance_config = self._load_performance_config()
        
        # Service availability cache
        self._service_availability_cache: Dict[ServiceType, bool] = {}
        self._cache_ttl = 300  # 5 minutes
        self._last_availability_check = 0
        
    def _initialize_service_capabilities(self) -> Dict[ServiceType, ServiceCapabilities]:
        """Initialize service capability profiles"""
        return {
            ServiceType.BASIC: ServiceCapabilities(
                service_type=ServiceType.BASIC,
                avg_response_time_ms=500,
                accuracy_score=0.6,
                supports_extreme_weights=False,
                supports_custom_styles=False,
                requires_ai_providers=False,
                fallback_available=True,
                resource_intensity=1
            ),
            ServiceType.FAST_VALIDATION: ServiceCapabilities(
                service_type=ServiceType.FAST_VALIDATION,
                avg_response_time_ms=1800,
                accuracy_score=0.8,
                supports_extreme_weights=True,
                supports_custom_styles=True,
                requires_ai_providers=True,
                fallback_available=True,
                resource_intensity=3
            ),
            ServiceType.FULL_VALIDATION: ServiceCapabilities(
                service_type=ServiceType.FULL_VALIDATION,
                avg_response_time_ms=4000,
                accuracy_score=0.95,
                supports_extreme_weights=True,
                supports_custom_styles=True,
                requires_ai_providers=True,
                fallback_available=True,
                resource_intensity=4
            ),
            ServiceType.COMPREHENSIVE: ServiceCapabilities(
                service_type=ServiceType.COMPREHENSIVE,
                avg_response_time_ms=6000,
                accuracy_score=0.98,
                supports_extreme_weights=True,
                supports_custom_styles=True,
                requires_ai_providers=True,
                fallback_available=False,
                resource_intensity=5
            )
        }
    
    def _load_performance_config(self) -> Dict[str, Any]:
        """Load performance configuration from environment"""
        config = {
            # Weight thresholds for service selection
            "light_weight_threshold_kg": 0.1,
            "heavy_weight_threshold_kg": 100.0,
            "extreme_weight_threshold_kg": 1000.0,
            
            # Timeout thresholds for service selection
            "fast_timeout_threshold_ms": 2000,
            "standard_timeout_threshold_ms": 5000,
            
            # Default service selection strategy
            "default_service_strategy": "smart_routing",
            "fallback_service_type": ServiceType.BASIC,
            
            # Environment-specific overrides
            "force_basic_in_development": False,
            "require_validation_in_production": True,
            
            # Performance tuning
            "ai_provider_preference": ["openai", "anthropic", "xai"],
            "cache_enabled": True,
            "parallel_validation_enabled": True
        }
        
        # Override with environment variables if available
        if self.env_manager:
            config.update(self._get_env_overrides())
        
        return config
    
    def _get_env_overrides(self) -> Dict[str, Any]:
        """Get configuration overrides from environment variables"""
        overrides = {}
        
        # Check for service factory specific environment variables
        if self.env_manager:
            # Service selection strategy
            strategy = self.env_manager.get_variable("SIZECOMPARATOR_SERVICE_STRATEGY")
            if strategy:
                overrides["default_service_strategy"] = strategy
            
            # Force basic service in development
            force_basic = self.env_manager.get_variable("SIZECOMPARATOR_FORCE_BASIC_SERVICE")
            if force_basic is not None:
                overrides["force_basic_in_development"] = force_basic
            
            # Require validation in production
            require_validation = self.env_manager.get_variable("SIZECOMPARATOR_REQUIRE_VALIDATION")
            if require_validation is not None:
                overrides["require_validation_in_production"] = require_validation
        
        return overrides
    
    def create_basic_service(self) -> BaseComparisonService:
        """Create basic comparison service for simple use cases"""
        try:
            # Import here to avoid circular imports
            from ..mvp_comparison import MVPComparisonService
            service = MVPComparisonService()
            self.logger.info("Created basic comparison service")
            return service
        except Exception as e:
            self.logger.error(f"Failed to create basic service: {e}")
            raise RuntimeError(f"Cannot create basic comparison service: {e}")
    
    def create_fast_validation_service(self) -> BaseComparisonService:
        """Create fast validation service optimized for <2 second responses"""
        try:
            service = FastValidationService()
            self.logger.info("Created fast validation service")
            return service
        except Exception as e:
            self.logger.error(f"Failed to create fast validation service: {e}")
            # Fallback to basic service
            self.logger.warning("Falling back to basic service")
            return self.create_basic_service()
    
    def create_full_validation_service(self) -> BaseComparisonService:
        """Create full validation service for maximum accuracy"""
        try:
            service = AIValidationService()
            self.logger.info("Created full validation service")
            return service
        except Exception as e:
            self.logger.error(f"Failed to create full validation service: {e}")
            # Fallback to fast validation service
            self.logger.warning("Falling back to fast validation service")
            return self.create_fast_validation_service()
    
    def create_comprehensive_service(self) -> BaseComparisonService:
        """Create comprehensive service with full features"""
        try:
            # For now, comprehensive service uses AI validation
            # In the future, this could use the full ComparisonService
            service = AIValidationService()
            self.logger.info("Created comprehensive service (using AI validation)")
            return service
        except Exception as e:
            self.logger.error(f"Failed to create comprehensive service: {e}")
            # Fallback to full validation service
            return self.create_full_validation_service()
    
    def get_optimal_service(self, requirements: ServiceRequirements) -> BaseComparisonService:
        """Get optimal service based on requirements using smart routing"""
        
        # Determine optimal service type
        optimal_type = self._determine_optimal_service_type(requirements)
        
        # Check service availability
        if not self._is_service_available(optimal_type):
            optimal_type = self._get_fallback_service_type(optimal_type)
        
        # Create and return service
        service = self._create_service_by_type(optimal_type)
        
        self.logger.info(
            f"Selected {optimal_type.value} service for weight={requirements.weight_kg}kg, "
            f"timeout={requirements.timeout_ms}ms, profile={requirements.performance_profile.value}"
        )
        
        return service
    
    def _determine_optimal_service_type(self, requirements: ServiceRequirements) -> ServiceType:
        """Determine optimal service type based on requirements"""
        
        weight_kg = requirements.weight_kg
        timeout_ms = requirements.timeout_ms
        profile = requirements.performance_profile
        
        # Check environment-specific overrides
        if self.env_manager:
            env_type = getattr(self.env_manager, 'environment', EnvironmentType.DEVELOPMENT)
            
            # Force basic in development if configured
            if (env_type == EnvironmentType.DEVELOPMENT and 
                self.performance_config.get("force_basic_in_development", False)):
                return ServiceType.BASIC
            
            # Require validation in production if configured
            if (env_type == EnvironmentType.PRODUCTION and 
                self.performance_config.get("require_validation_in_production", True)):
                if profile == PerformanceProfile.SPEED_OPTIMIZED:
                    return ServiceType.FAST_VALIDATION
                else:
                    return ServiceType.FULL_VALIDATION
        
        # Performance profile based selection
        if profile == PerformanceProfile.SPEED_OPTIMIZED:
            if timeout_ms <= self.performance_config["fast_timeout_threshold_ms"]:
                return self._select_fast_service(weight_kg)
            else:
                return ServiceType.FAST_VALIDATION
        
        elif profile == PerformanceProfile.ACCURACY_OPTIMIZED:
            if self._is_extreme_weight(weight_kg):
                return ServiceType.FULL_VALIDATION
            else:
                return ServiceType.COMPREHENSIVE
        
        else:  # BALANCED profile
            return self._select_balanced_service(weight_kg, timeout_ms, requirements)
    
    def _select_fast_service(self, weight_kg: float) -> ServiceType:
        """Select fastest appropriate service for weight"""
        if self._is_common_weight(weight_kg):
            return ServiceType.BASIC
        else:
            return ServiceType.FAST_VALIDATION
    
    def _select_balanced_service(self, weight_kg: float, timeout_ms: int, 
                                requirements: ServiceRequirements) -> ServiceType:
        """Select balanced service considering all factors"""
        
        # For extreme weights, prefer validation services
        if self._is_extreme_weight(weight_kg):
            if timeout_ms <= self.performance_config["fast_timeout_threshold_ms"]:
                return ServiceType.FAST_VALIDATION
            else:
                return ServiceType.FULL_VALIDATION
        
        # For common weights, consider timeout and accuracy priority
        if timeout_ms <= self.performance_config["fast_timeout_threshold_ms"]:
            if requirements.accuracy_priority:
                return ServiceType.FAST_VALIDATION
            else:
                return ServiceType.BASIC
        
        elif timeout_ms <= self.performance_config["standard_timeout_threshold_ms"]:
            return ServiceType.FAST_VALIDATION
        
        else:
            return ServiceType.FULL_VALIDATION
    
    def _is_common_weight(self, weight_kg: float) -> bool:
        """Check if weight is in common range (easy to compare)"""
        light_threshold = self.performance_config["light_weight_threshold_kg"]
        heavy_threshold = self.performance_config["heavy_weight_threshold_kg"]
        return light_threshold <= weight_kg <= heavy_threshold
    
    def _is_extreme_weight(self, weight_kg: float) -> bool:
        """Check if weight is extreme (requires special handling)"""
        light_threshold = self.performance_config["light_weight_threshold_kg"]
        extreme_threshold = self.performance_config["extreme_weight_threshold_kg"]
        return weight_kg < light_threshold or weight_kg > extreme_threshold
    
    def _is_service_available(self, service_type: ServiceType) -> bool:
        """Check if service type is available"""
        import time
        
        # Check cache first
        current_time = time.time()
        if (current_time - self._last_availability_check) < self._cache_ttl:
            cached_result = self._service_availability_cache.get(service_type)
            if cached_result is not None:
                return cached_result
        
        # Check actual availability
        availability = self._check_service_availability(service_type)
        
        # Update cache
        self._service_availability_cache[service_type] = availability
        self._last_availability_check = current_time
        
        return availability
    
    def _check_service_availability(self, service_type: ServiceType) -> bool:
        """Actually check if service is available"""
        capabilities = self.service_capabilities[service_type]
        
        # Basic service is always available
        if service_type == ServiceType.BASIC:
            return True
        
        # Check if AI providers are required and available
        if capabilities.requires_ai_providers:
            if not self._are_ai_providers_available():
                return False
        
        # Additional availability checks could be added here
        # (e.g., resource constraints, external dependencies)
        
        return True
    
    def _are_ai_providers_available(self) -> bool:
        """Check if AI providers are configured and available"""
        if not self.env_manager:
            return False
        
        # Check if at least one AI provider key is configured
        openai_key = self.env_manager.get_variable("SIZECOMPARATOR_OPENAI_API_KEY", mask_sensitive=False)
        anthropic_key = self.env_manager.get_variable("SIZECOMPARATOR_ANTHROPIC_API_KEY", mask_sensitive=False)
        xai_key = self.env_manager.get_variable("SIZECOMPARATOR_XAI_API_KEY", mask_sensitive=False)
        
        return bool(openai_key or anthropic_key or xai_key)
    
    def _get_fallback_service_type(self, preferred_type: ServiceType) -> ServiceType:
        """Get fallback service type when preferred is unavailable"""
        fallback_chain = {
            ServiceType.COMPREHENSIVE: ServiceType.FULL_VALIDATION,
            ServiceType.FULL_VALIDATION: ServiceType.FAST_VALIDATION,
            ServiceType.FAST_VALIDATION: ServiceType.BASIC,
            ServiceType.BASIC: ServiceType.BASIC  # Basic is always available
        }
        
        fallback = fallback_chain.get(preferred_type, ServiceType.BASIC)
        
        # Check if fallback is available
        if self._is_service_available(fallback):
            return fallback
        
        # If fallback not available, continue down the chain
        if fallback != ServiceType.BASIC:
            return self._get_fallback_service_type(fallback)
        
        return ServiceType.BASIC
    
    def _create_service_by_type(self, service_type: ServiceType) -> BaseComparisonService:
        """Create service instance by type"""
        if service_type == ServiceType.BASIC:
            return self.create_basic_service()
        elif service_type == ServiceType.FAST_VALIDATION:
            return self.create_fast_validation_service()
        elif service_type == ServiceType.FULL_VALIDATION:
            return self.create_full_validation_service()
        elif service_type == ServiceType.COMPREHENSIVE:
            return self.create_comprehensive_service()
        else:
            self.logger.warning(f"Unknown service type {service_type}, using basic")
            return self.create_basic_service()
    
    def get_service_from_request(self, request: MVPComparisonRequest) -> BaseComparisonService:
        """Get optimal service based on request parameters"""
        
        # Extract weight information
        weight_kg = self._extract_weight_from_request(request)
        
        # Determine requirements from request
        requirements = ServiceRequirements(
            weight_kg=weight_kg,
            timeout_ms=self._get_timeout_from_request(request),
            accuracy_priority=self._is_accuracy_priority(request),
            speed_priority=self._is_speed_priority(request),
            performance_profile=self._get_performance_profile_from_request(request)
        )
        
        return self.get_optimal_service(requirements)
    
    def _extract_weight_from_request(self, request: MVPComparisonRequest) -> float:
        """Extract weight in kg from request"""
        try:
            # Use weight processor to parse weight
            from ..weight_processor import WeightProcessor
            processor = WeightProcessor()
            processed = processor.process_weight(request.weight_input)
            return float(processed.weight_kg)
        except Exception as e:
            self.logger.warning(f"Failed to extract weight from request: {e}")
            # Return default weight in common range
            return 5.0
    
    def _get_timeout_from_request(self, request: MVPComparisonRequest) -> int:
        """Get timeout requirement from request (default 3000ms)"""
        # In the future, this could be extracted from request headers or params
        return 3000
    
    def _is_accuracy_priority(self, request: MVPComparisonRequest) -> bool:
        """Check if request prioritizes accuracy"""
        return request.style in ["technical", "detailed"]
    
    def _is_speed_priority(self, request: MVPComparisonRequest) -> bool:
        """Check if request prioritizes speed"""
        return request.provider == "auto" and request.style == "default"
    
    def _get_performance_profile_from_request(self, request: MVPComparisonRequest) -> PerformanceProfile:
        """Determine performance profile from request"""
        if self._is_speed_priority(request):
            return PerformanceProfile.SPEED_OPTIMIZED
        elif self._is_accuracy_priority(request):
            return PerformanceProfile.ACCURACY_OPTIMIZED
        else:
            return PerformanceProfile.BALANCED
    
    def get_service_health_status(self) -> Dict[str, Any]:
        """Get health status of all available services"""
        status = {
            "factory_status": "healthy",
            "services": {},
            "availability": {},
            "performance_config": self.performance_config,
            "ai_providers_available": self._are_ai_providers_available()
        }
        
        # Check availability of each service type
        for service_type in ServiceType:
            try:
                available = self._is_service_available(service_type)
                status["availability"][service_type.value] = available
                
                if available:
                    # Get capabilities
                    capabilities = self.service_capabilities[service_type]
                    status["services"][service_type.value] = {
                        "avg_response_time_ms": capabilities.avg_response_time_ms,
                        "accuracy_score": capabilities.accuracy_score,
                        "resource_intensity": capabilities.resource_intensity
                    }
            except Exception as e:
                status["availability"][service_type.value] = False
                status["services"][service_type.value] = {"error": str(e)}
        
        return status
    
    def clear_availability_cache(self):
        """Clear service availability cache to force fresh checks"""
        self._service_availability_cache.clear()
        self._last_availability_check = 0
        self.logger.info("Service availability cache cleared")


# Convenience functions for common use cases

def create_service_for_weight(weight_input: str, 
                            timeout_ms: int = 3000,
                            env_manager: Optional[EnvironmentManager] = None) -> BaseComparisonService:
    """Create optimal service for a specific weight input"""
    factory = ComparisonServiceFactory(env_manager)
    
    # Create mock request to determine requirements
    from models.mvp import MVPComparisonRequest
    request = MVPComparisonRequest(weight_input=weight_input)
    
    return factory.get_service_from_request(request)


def create_fast_service(env_manager: Optional[EnvironmentManager] = None) -> BaseComparisonService:
    """Create fastest available service (for speed-critical applications)"""
    factory = ComparisonServiceFactory(env_manager)
    requirements = ServiceRequirements(
        weight_kg=5.0,  # Common weight
        timeout_ms=1500,
        speed_priority=True,
        performance_profile=PerformanceProfile.SPEED_OPTIMIZED
    )
    return factory.get_optimal_service(requirements)


def create_accurate_service(env_manager: Optional[EnvironmentManager] = None) -> BaseComparisonService:
    """Create most accurate service (for accuracy-critical applications)"""
    factory = ComparisonServiceFactory(env_manager)
    requirements = ServiceRequirements(
        weight_kg=5.0,  # Common weight
        timeout_ms=8000,
        accuracy_priority=True,
        performance_profile=PerformanceProfile.ACCURACY_OPTIMIZED
    )
    return factory.get_optimal_service(requirements)


def create_default_service(env_manager: Optional[EnvironmentManager] = None) -> BaseComparisonService:
    """Create balanced default service for general use"""
    factory = ComparisonServiceFactory(env_manager)
    requirements = ServiceRequirements(
        weight_kg=5.0,  # Common weight
        timeout_ms=3000,
        performance_profile=PerformanceProfile.BALANCED
    )
    return factory.get_optimal_service(requirements)


# Global factory instance for applications that need a singleton
_global_factory: Optional[ComparisonServiceFactory] = None


def get_global_factory(env_manager: Optional[EnvironmentManager] = None) -> ComparisonServiceFactory:
    """Get or create global factory instance"""
    global _global_factory
    if _global_factory is None:
        _global_factory = ComparisonServiceFactory(env_manager)
    return _global_factory


def reset_global_factory():
    """Reset global factory instance (useful for testing)"""
    global _global_factory
    _global_factory = None