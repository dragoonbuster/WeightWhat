"""
SizeComparator Data Models Package

Simplified model imports aligned with actual working code.
This package contains only the models that are actually used in the system.
"""

# MVP models - primary models for working applications
from .mvp import (
    MVPComparisonRequest,
    MVPComparisonResponse,
    MVPErrorResponse
)

# Core weight models - used by AI providers
from .weight import (
    WeightUnit,
    WeightInput,
    ProcessedWeight,
    WeightProcessor
)

# Error models - used by error handling
from .errors import (
    ErrorCategory,
    ErrorSeverity,
    BaseErrorResponse
)

# Response models - used by API endpoints
from .responses import (
    MetricsResponse,
    WeightComparisonResponse,
    HealthCheckResponse,
    ReadinessResponse,
    ReadinessCheck
)

# Request models - used by API endpoints
from .requests import (
    WeightComparisonRequest
)

# Configuration models - removed, using simple configuration system now
# from .config import (
#     ApplicationConfiguration as ApplicationConfig,
#     ConfigurationValidator
# )

# Version information
__version__ = "1.0.0"
__author__ = "SizeComparator Team"

# Export commonly used models
__all__ = [
    # MVP models (primary interface)
    "MVPComparisonRequest",
    "MVPComparisonResponse", 
    "MVPErrorResponse",
    
    # Core weight models
    "WeightUnit",
    "WeightInput",
    "ProcessedWeight",
    "WeightProcessor",
    
    # Error models
    "ErrorCategory",
    "ErrorSeverity",
    "BaseErrorResponse",
    
    # Response models  
    "MetricsResponse",
    "WeightComparisonResponse",
    "HealthCheckResponse",
    "ReadinessResponse",
    "ReadinessCheck",
    
    # Request models
    "WeightComparisonRequest",
    
    # Configuration models (removed - using simple configuration system)
    # "ApplicationConfig",
    # "ConfigurationValidator"
]