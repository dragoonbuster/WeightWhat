"""
SizeComparator Data Models Package

This package contains all Pydantic models for SizeComparator as specified in DATA_MODELS_SPEC.
It provides comprehensive type safety, validation, and serialization for all system components.

The models are organized into the following modules:
- weight: Core weight models and enums
- requests: API request models
- responses: API response models  
- errors: Error response models aligned with ERROR_MONITORING_SPEC
- providers: AI provider models for AI_PROVIDER_SPEC integration
- config: Configuration and template models for CONFIG_SYSTEM_SPEC

All models use Pydantic V2 for enhanced performance and validation capabilities.
"""

# Core weight models and enums
from .weight import (
    WeightUnit,
    ComparisonType,
    WeightInput,
    ProcessedWeight,
    WeightValidators,
    WeightProcessor
)

# Request models
from .requests import (
    WeightComparisonRequest,
    ProviderSelectionRequest,
    ConfigurationReloadRequest
)

# Response models
from .responses import (
    ComparisonAnalysis,
    AIVisualizationPrompt,
    ResponseMetadata,
    WeightComparisonResponse,
    ProviderSelectionResponse,
    HealthCheckResponse,
    ReadinessCheck,
    ReadinessResponse,
    MetricsResponse,
    ConfigurationValidationResult,
    ConfigurationReloadResponse
)

# Error models
from .errors import (
    ErrorCategory,
    ErrorSeverity,
    FieldError,
    ErrorContext,
    BaseErrorResponse,
    ValidationErrorResponse,
    BusinessLogicErrorResponse,
    IntegrationErrorResponse,
    ServerErrorResponse,
    ErrorFactory
)

# AI Provider models
from .providers import (
    AIProvider,
    ProviderStatus,
    CircuitBreakerState,
    AIProviderRequest,
    AIProviderMetadata,
    AIProviderHealth,
    AIProviderResponse,
    ProviderConfiguration,
    ComparisonCategory,
    TemplateVariables,
    ProviderFallbackConfig,
    ProviderMetrics,
    ComponentHealth
)

# Configuration models
from .config import (
    ConfigurationError,
    TemplateType,
    TemplateValidationResult,
    TemplateConfig,
    APIConfiguration,
    CacheConfiguration,
    LoggingConfiguration,
    MonitoringConfiguration,
    SecurityConfiguration,
    ApplicationConfiguration,
    ConfigurationValidator
)

# Version information
__version__ = "1.0.0"
__author__ = "SizeComparator Team"

# Model collections for easier importing
REQUEST_MODELS = [
    WeightComparisonRequest,
    ProviderSelectionRequest,
    ConfigurationReloadRequest
]

RESPONSE_MODELS = [
    WeightComparisonResponse,
    ProviderSelectionResponse,
    HealthCheckResponse,
    ReadinessResponse,
    MetricsResponse,
    ConfigurationReloadResponse
]

ERROR_MODELS = [
    BaseErrorResponse,
    ValidationErrorResponse,
    BusinessLogicErrorResponse,
    IntegrationErrorResponse,
    ServerErrorResponse
]

PROVIDER_MODELS = [
    AIProviderRequest,
    AIProviderResponse,
    AIProviderHealth,
    ProviderConfiguration,
    ProviderMetrics
]

CONFIG_MODELS = [
    ApplicationConfiguration,
    TemplateConfig,
    APIConfiguration,
    CacheConfiguration,
    LoggingConfiguration,
    MonitoringConfiguration,
    SecurityConfiguration
]

WEIGHT_MODELS = [
    WeightInput,
    ProcessedWeight
]

# All models for validation and documentation
ALL_MODELS = (
    REQUEST_MODELS +
    RESPONSE_MODELS +
    ERROR_MODELS +
    PROVIDER_MODELS +
    CONFIG_MODELS +
    WEIGHT_MODELS
)

# Utility functions
def get_model_by_name(name: str):
    """Get a model class by its name."""
    for model in ALL_MODELS:
        if model.__name__ == name:
            return model
    raise ValueError(f"Model '{name}' not found")

def list_models():
    """List all available models."""
    return [model.__name__ for model in ALL_MODELS]

def validate_model_data(model_name: str, data: dict):
    """Validate data against a specific model."""
    model_class = get_model_by_name(model_name)
    return model_class(**data)

# Export everything for easy access
__all__ = [
    # Core weight models
    "WeightUnit",
    "ComparisonType", 
    "WeightInput",
    "ProcessedWeight",
    "WeightValidators",
    "WeightProcessor",
    
    # Request models
    "WeightComparisonRequest",
    "ProviderSelectionRequest",
    "ConfigurationReloadRequest",
    
    # Response models
    "ComparisonAnalysis",
    "AIVisualizationPrompt",
    "ResponseMetadata",
    "WeightComparisonResponse",
    "ProviderSelectionResponse",
    "HealthCheckResponse",
    "ReadinessCheck",
    "ReadinessResponse",
    "MetricsResponse",
    "ConfigurationValidationResult",
    "ConfigurationReloadResponse",
    
    # Error models
    "ErrorCategory",
    "ErrorSeverity",
    "FieldError",
    "ErrorContext",
    "BaseErrorResponse",
    "ValidationErrorResponse",
    "BusinessLogicErrorResponse",
    "IntegrationErrorResponse",
    "ServerErrorResponse",
    "ErrorFactory",
    
    # AI Provider models
    "AIProvider",
    "ProviderStatus",
    "CircuitBreakerState",
    "AIProviderRequest",
    "AIProviderMetadata",
    "AIProviderHealth",
    "AIProviderResponse",
    "ProviderConfiguration",
    "ComparisonCategory",
    "TemplateVariables",
    "ProviderFallbackConfig",
    "ProviderMetrics",
    "ComponentHealth",
    
    # Configuration models
    "ConfigurationError",
    "TemplateType",
    "TemplateValidationResult",
    "TemplateConfig",
    "APIConfiguration",
    "CacheConfiguration",
    "LoggingConfiguration",
    "MonitoringConfiguration",
    "SecurityConfiguration",
    "ApplicationConfiguration",
    "ConfigurationValidator",
    
    # Model collections
    "REQUEST_MODELS",
    "RESPONSE_MODELS",
    "ERROR_MODELS",
    "PROVIDER_MODELS",
    "CONFIG_MODELS",
    "WEIGHT_MODELS",
    "ALL_MODELS",
    
    # Utility functions
    "get_model_by_name",
    "list_models",
    "validate_model_data"
]