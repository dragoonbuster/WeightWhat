"""
AI Provider models for SizeComparator matching AI_PROVIDER_SPEC.

This module contains all AI provider interface models including health tracking,
circuit breaker states, and provider responses.
"""

from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any, Literal, Annotated
from decimal import Decimal
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum
import re


class AIProvider(str, Enum):
    """Supported AI providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    XAI = "xai"


class ProviderStatus(str, Enum):
    """AI provider status from AI_PROVIDER_SPEC."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CIRCUIT_OPEN = "circuit_open"


class CircuitBreakerState(str, Enum):
    """Circuit breaker states from AI_PROVIDER_SPEC."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting calls
    HALF_OPEN = "half_open"  # Testing recovery


class AIProviderRequest(BaseModel):
    """Request to AI provider from AI_PROVIDER_SPEC."""
    prompt_template_id: str = Field(
        ...,
        pattern=r'^[a-zA-Z0-9_-]+$',
        description="Template ID from CONFIG_SYSTEM_SPEC"
    )
    template_variables: Dict[str, Any] = Field(
        default_factory=dict,
        description="Variables for template rendering"
    )
    weight_data: Dict[str, Any] = Field(
        ...,
        description="Weight comparison data"
    )
    max_tokens: Annotated[int, Field(ge=50, le=2000)] = Field(
        500,
        description="Maximum response tokens"
    )
    temperature: Annotated[float, Field(ge=0.0, le=2.0)] = Field(
        0.7,
        description="AI generation temperature"
    )
    timeout_seconds: Annotated[float, Field(ge=1.0, le=60.0)] = Field(
        30.0,
        description="Request timeout"
    )
    request_id: UUID = Field(
        default_factory=uuid4,
        description="Request correlation ID"
    )
    retry_count: Annotated[int, Field(ge=0, le=3)] = Field(
        0,
        description="Current retry attempt"
    )


class AIProviderMetadata(BaseModel):
    """Metadata about AI provider response."""
    provider_name: str = Field(
        ...,
        description="Name of AI provider used"
    )
    model_name: str = Field(
        ...,
        description="Specific model used"
    )
    response_time_ms: Annotated[int, Field(ge=0)] = Field(
        ...,
        description="Provider response time"
    )
    tokens_used: Optional[int] = Field(
        None,
        ge=0,
        description="Tokens consumed"
    )
    cost_estimate: Optional[Decimal] = Field(
        None,
        description="Estimated cost in USD"
    )
    rate_limit_remaining: Optional[int] = Field(
        None,
        ge=0,
        description="Remaining rate limit quota"
    )
    rate_limit_reset: Optional[datetime] = Field(
        None,
        description="When rate limit resets"
    )
    provider_request_id: Optional[str] = Field(
        None,
        description="Provider's internal request ID"
    )


class AIProviderHealth(BaseModel):
    """AI provider health status for DEPLOYMENT_OPS_SPEC."""
    provider_name: str = Field(
        ...,
        description="Provider identifier"
    )
    status: ProviderStatus = Field(
        ...,
        description="Current provider health status"
    )
    circuit_breaker_state: CircuitBreakerState = Field(
        ...,
        description="Circuit breaker state"
    )
    success_rate: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        ...,
        description="Recent success rate (0-1)"
    )
    avg_response_time_ms: Annotated[float, Field(ge=0.0)] = Field(
        ...,
        description="Average response time"
    )
    error_count: Annotated[int, Field(ge=0)] = Field(
        ...,
        description="Recent error count"
    )
    last_success: Optional[datetime] = Field(
        None,
        description="Last successful request timestamp"
    )
    last_error: Optional[str] = Field(
        None,
        max_length=500,
        description="Last error message"
    )
    requests_per_minute: Annotated[int, Field(ge=0)] = Field(
        ...,
        description="Current request rate"
    )
    rate_limit_quota: Optional[int] = Field(
        None,
        description="Rate limit quota"
    )
    circuit_breaker_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Circuit breaker configuration"
    )


class AIProviderResponse(BaseModel):
    """Response from AI provider with validation."""
    content: Annotated[str, Field(
        min_length=10,
        max_length=5000
    )] = Field(
        ...,
        description="Generated content"
    )
    confidence_score: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        ...,
        description="AI confidence in response quality"
    )
    metadata: AIProviderMetadata = Field(
        ...,
        description="Provider response metadata"
    )
    validation_passed: bool = Field(
        ...,
        description="Whether response passed validation"
    )
    validation_errors: List[str] = Field(
        default_factory=list,
        max_items=10,
        description="Validation errors if any"
    )
    fallback_used: bool = Field(
        False,
        description="Whether fallback provider was used"
    )
    original_provider: Optional[str] = Field(
        None,
        description="Original provider if fallback was used"
    )
    
    @field_validator('content')
    @classmethod
    def validate_content_quality(cls, v: str) -> str:
        """Validate AI response content quality."""
        # Check for common failure patterns
        failure_patterns = [
            r'(?i)as an ai language model',
            r'(?i)i cannot generate',
            r'(?i)error occurred',
            r'(?i)please try again'
        ]
        
        for pattern in failure_patterns:
            if re.search(pattern, v):
                raise ValueError(f"AI response contains failure pattern")
        
        return v


class ProviderConfiguration(BaseModel):
    """Configuration for an AI provider."""
    provider_name: str = Field(
        ...,
        description="Provider identifier"
    )
    api_key: str = Field(
        ...,
        description="API key for the provider"
    )
    base_url: Optional[str] = Field(
        None,
        description="Custom base URL if needed"
    )
    timeout_seconds: Annotated[float, Field(ge=1.0, le=120.0)] = Field(
        30.0,
        description="Request timeout"
    )
    max_retries: Annotated[int, Field(ge=0, le=5)] = Field(
        3,
        description="Maximum retry attempts"
    )
    rate_limit_rpm: Optional[int] = Field(
        None,
        ge=1,
        description="Requests per minute limit"
    )
    circuit_breaker_enabled: bool = Field(
        True,
        description="Whether to use circuit breaker"
    )
    circuit_breaker_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Circuit breaker configuration"
    )
    priority: Annotated[int, Field(ge=1, le=10)] = Field(
        5,
        description="Provider priority (1=highest, 10=lowest)"
    )
    enabled: bool = Field(
        True,
        description="Whether provider is enabled"
    )


class ComparisonCategory(str, Enum):
    """Categories for weight comparisons."""
    ANIMAL_VS_ANIMAL = "animal_vs_animal"
    VEHICLE_VS_VEHICLE = "vehicle_vs_vehicle"
    ANIMAL_VS_VEHICLE = "animal_vs_vehicle"
    FOOD_VS_FOOD = "food_vs_food"
    OBJECT_VS_OBJECT = "object_vs_object"
    MIXED = "mixed"
    UNKNOWN = "unknown"


class TemplateVariables(BaseModel):
    """Variables for AI prompt templates."""
    item1_name: str = Field(
        ...,
        description="Name of first item"
    )
    item1_weight: str = Field(
        ...,
        description="Weight of first item with unit"
    )
    item2_name: str = Field(
        ...,
        description="Name of second item"
    )
    item2_weight: str = Field(
        ...,
        description="Weight of second item with unit"
    )
    weight_ratio: float = Field(
        ...,
        description="Ratio of item1/item2 weights"
    )
    percentage_difference: float = Field(
        ...,
        description="Percentage difference between weights"
    )
    heavier_item: str = Field(
        ...,
        description="Which item is heavier"
    )
    comparison_category: ComparisonCategory = Field(
        ...,
        description="Category of comparison"
    )
    significance_level: str = Field(
        ...,
        description="Significance of weight difference"
    )
    output_unit: str = Field(
        ...,
        description="Preferred output unit"
    )
    locale: str = Field(
        "en-US",
        description="Locale for formatting"
    )


class ProviderFallbackConfig(BaseModel):
    """Configuration for provider fallback logic."""
    enabled: bool = Field(
        True,
        description="Whether fallback is enabled"
    )
    fallback_chain: List[str] = Field(
        ...,
        description="Ordered list of fallback providers"
    )
    max_fallback_attempts: Annotated[int, Field(ge=1, le=5)] = Field(
        3,
        description="Maximum fallback attempts"
    )
    fallback_timeout_seconds: Annotated[float, Field(ge=1.0, le=60.0)] = Field(
        15.0,
        description="Timeout for fallback attempts"
    )
    require_same_confidence: bool = Field(
        False,
        description="Whether fallback must match original confidence"
    )


class ProviderMetrics(BaseModel):
    """Metrics for provider monitoring."""
    provider_name: str = Field(
        ...,
        description="Provider identifier"
    )
    requests_total: Annotated[int, Field(ge=0)] = Field(
        ...,
        description="Total requests made"
    )
    requests_successful: Annotated[int, Field(ge=0)] = Field(
        ...,
        description="Successful requests"
    )
    requests_failed: Annotated[int, Field(ge=0)] = Field(
        ...,
        description="Failed requests"
    )
    avg_response_time_ms: Annotated[float, Field(ge=0.0)] = Field(
        ...,
        description="Average response time"
    )
    p95_response_time_ms: Annotated[float, Field(ge=0.0)] = Field(
        ...,
        description="95th percentile response time"
    )
    total_tokens_used: Annotated[int, Field(ge=0)] = Field(
        ...,
        description="Total tokens consumed"
    )
    total_cost: Decimal = Field(
        ...,
        description="Total cost in USD"
    )
    last_24h_requests: Annotated[int, Field(ge=0)] = Field(
        ...,
        description="Requests in last 24 hours"
    )
    circuit_breaker_trips: Annotated[int, Field(ge=0)] = Field(
        ...,
        description="Number of circuit breaker trips"
    )


class ComponentHealth(BaseModel):
    """Health status of individual system components."""
    name: str = Field(
        ...,
        description="Component name"
    )
    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ...,
        description="Component health status"
    )
    last_check: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last health check timestamp"
    )
    response_time_ms: Optional[int] = Field(
        None,
        ge=0,
        description="Component response time"
    )
    error_message: Optional[str] = Field(
        None,
        max_length=500,
        description="Error message if unhealthy"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Component-specific health data"
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Component dependencies"
    )