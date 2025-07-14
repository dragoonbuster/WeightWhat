"""
Response models for SizeComparator API endpoints.

This module contains all response models including weight comparison results,
analysis data, and metadata as specified in the DATA_MODELS_SPEC.
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional, List, Dict, Any, Union, Literal, Annotated
from decimal import Decimal
from datetime import datetime
from uuid import UUID

from .weight import ProcessedWeight, WeightInput, WeightUnit


class ComparisonAnalysis(BaseModel):
    """Detailed comparison analysis results."""
    weight_ratio: Decimal = Field(
        ...,
        description="Ratio of item1/item2 weights"
    )
    percentage_difference: Decimal = Field(
        ...,
        description="Percentage difference between weights"
    )
    absolute_difference: ProcessedWeight = Field(
        ...,
        description="Absolute weight difference"
    )
    heavier_item: Literal["item1", "item2", "equal"] = Field(
        ...,
        description="Which item is heavier"
    )
    significance_level: Literal["negligible", "small", "moderate", "large", "extreme"] = Field(
        ...,
        description="Significance of weight difference"
    )
    comparison_category: str = Field(
        ...,
        max_length=100,
        description="Category of comparison (e.g., 'animal_vs_vehicle')"
    )
    equivalent_objects: Optional[List[Dict[str, Any]]] = Field(
        None,
        max_items=5,
        description="List of equivalent weight objects for context"
    )
    
    @field_validator('significance_level', mode='before')
    @classmethod
    def determine_significance(cls, v: Any, info) -> str:
        """Automatically determine significance based on ratio."""
        if v is not None:  # If already set, use it
            return v
            
        ratio = info.data.get('weight_ratio', 1)
        if isinstance(ratio, Decimal):
            ratio = float(ratio)
            
        if abs(ratio - 1) < 0.01:
            return "negligible"
        elif ratio < 2:
            return "small"
        elif ratio < 10:
            return "moderate"
        elif ratio < 100:
            return "large"
        else:
            return "extreme"


class AIVisualizationPrompt(BaseModel):
    """AI-generated visualization prompt from AI_PROVIDER_SPEC."""
    prompt_text: Annotated[str, Field(
        min_length=10,
        max_length=2000
    )] = Field(
        ...,
        description="Generated visualization prompt"
    )
    provider_used: str = Field(
        ...,
        description="AI provider that generated the prompt"
    )
    generation_time_ms: Annotated[int, Field(ge=0)] = Field(
        ...,
        description="Time taken to generate prompt"
    )
    confidence_score: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        ...,
        description="AI confidence in prompt quality"
    )
    prompt_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific metadata"
    )
    fallback_used: bool = Field(
        False,
        description="Whether fallback generation was used"
    )
    template_id: Optional[str] = Field(
        None,
        description="CONFIG_SYSTEM_SPEC template ID used"
    )


class ResponseMetadata(BaseModel):
    """Response metadata for debugging and monitoring."""
    request_id: UUID = Field(
        ...,
        description="Original request correlation ID"
    )
    processing_time_ms: Annotated[int, Field(ge=0)] = Field(
        ...,
        description="Total processing time"
    )
    component_timings: Dict[str, int] = Field(
        default_factory=dict,
        description="Processing time breakdown by component"
    )
    ai_provider_used: Optional[str] = Field(
        None,
        description="AI provider used for visualization"
    )
    ai_response_time_ms: Optional[int] = Field(
        None,
        description="AI provider response time"
    )
    cache_hit: bool = Field(
        False,
        description="Whether response was served from cache"
    )
    warnings: List[str] = Field(
        default_factory=list,
        max_items=20,
        description="Processing warnings"
    )
    api_version: str = Field(
        ...,
        pattern=r'^\d+\.\d+\.\d+$',
        description="API version used"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response generation timestamp"
    )


class WeightComparisonResponse(BaseModel):
    """Complete response model for weight comparisons."""
    model_config = ConfigDict(
        json_encoders={
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        },
        json_schema_extra={
            "example": {
                "item1": {
                    "original_input": {"value": "5000 kg", "confidence": 0.95},
                    "parsed_value": 5000.0,
                    "display_value": "5,000 kg",
                    "unit_used": "kg",
                    "parsing_confidence": 1.0
                },
                "item2": {
                    "original_input": {"value": 1611.0, "unit": "kg"},
                    "parsed_value": 1611.0,
                    "display_value": "1,611 kg",
                    "unit_used": "kg",
                    "parsing_confidence": 1.0
                },
                "analysis": {
                    "weight_ratio": 3.105,
                    "percentage_difference": 210.49,
                    "heavier_item": "item1",
                    "significance_level": "moderate",
                    "comparison_category": "animal_vs_vehicle"
                },
                "visualization": {
                    "prompt_text": "Create a visual comparison...",
                    "provider_used": "openai",
                    "generation_time_ms": 245,
                    "confidence_score": 0.92
                },
                "metadata": {
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                    "processing_time_ms": 312,
                    "api_version": "1.0.0",
                    "timestamp": "2025-07-13T10:30:00Z"
                }
            }
        }
    )
    
    item1: ProcessedWeight = Field(
        ...,
        description="Processed weight for first item"
    )
    item2: ProcessedWeight = Field(
        ...,
        description="Processed weight for second item"
    )
    analysis: ComparisonAnalysis = Field(
        ...,
        description="Detailed comparison analysis"
    )
    visualization: Optional[AIVisualizationPrompt] = Field(
        None,
        description="AI-generated visualization prompt"
    )
    metadata: ResponseMetadata = Field(
        ...,
        description="Response metadata"
    )


class ProviderSelectionResponse(BaseModel):
    """Response from provider selection logic."""
    selected_provider: str = Field(
        ...,
        description="Selected provider name"
    )
    selection_reason: str = Field(
        ...,
        description="Reason for selection"
    )
    alternative_providers: List[str] = Field(
        default_factory=list,
        description="Alternative providers in priority order"
    )
    estimated_cost: Optional[Decimal] = Field(
        None,
        description="Estimated cost for request"
    )
    estimated_response_time_ms: int = Field(
        ...,
        description="Estimated response time"
    )


class HealthCheckResponse(BaseModel):
    """Primary health check response for DEPLOYMENT_OPS_SPEC."""
    status: Literal["healthy", "degraded", "unhealthy"] = Field(
        ...,
        description="Overall system health status"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Health check timestamp"
    )
    version: str = Field(
        ...,
        pattern=r'^\d+\.\d+\.\d+$',
        description="Application version"
    )
    environment: str = Field(
        ...,
        description="Deployment environment"
    )
    uptime_seconds: Annotated[int, Field(ge=0)] = Field(
        ...,
        description="System uptime in seconds"
    )
    components: Dict[str, Any] = Field(
        default_factory=dict,
        description="Individual component health statuses"
    )
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        },
        json_schema_extra={
            "example": {
                "status": "degraded",
                "timestamp": "2025-07-13T10:30:00Z",
                "version": "1.0.0",
                "environment": "production",
                "uptime_seconds": 3600,
                "components": {
                    "api": {
                        "name": "api",
                        "status": "healthy",
                        "last_check": "2025-07-13T10:30:00Z",
                        "response_time_ms": 5
                    },
                    "ai_providers": {
                        "name": "ai_providers",
                        "status": "degraded",
                        "last_check": "2025-07-13T10:30:00Z",
                        "metadata": {
                            "openai": "healthy",
                            "anthropic": "circuit_open",
                            "xai": "healthy"
                        }
                    },
                    "cache": {
                        "name": "cache",
                        "status": "healthy",
                        "last_check": "2025-07-13T10:30:00Z",
                        "response_time_ms": 2
                    }
                }
            }
        }
    )
    
    @model_validator(mode='after')
    def determine_overall_status(self) -> 'HealthCheckResponse':
        """Determine overall status from component statuses."""
        if not self.components:
            return self
            
        unhealthy_count = sum(1 for c in self.components.values() 
                             if isinstance(c, dict) and c.get("status") == "unhealthy")
        degraded_count = sum(1 for c in self.components.values() 
                            if isinstance(c, dict) and c.get("status") == "degraded")
        
        if unhealthy_count > 0:
            self.status = "unhealthy"
        elif degraded_count > 0:
            self.status = "degraded"
        else:
            self.status = "healthy"
            
        return self


class ReadinessCheck(BaseModel):
    """Individual readiness check item."""
    check_name: str = Field(
        ...,
        description="Name of the readiness check"
    )
    status: Literal["pass", "fail", "warn"] = Field(
        ...,
        description="Check result status"
    )
    message: Optional[str] = Field(
        None,
        max_length=500,
        description="Check result message"
    )
    duration_ms: Annotated[int, Field(ge=0)] = Field(
        ...,
        description="Check execution time"
    )
    required: bool = Field(
        True,
        description="Whether this check is required for readiness"
    )
    threshold: Optional[Dict[str, Any]] = Field(
        None,
        description="Threshold values for the check"
    )


class ReadinessResponse(BaseModel):
    """Readiness check response for DEPLOYMENT_OPS_SPEC."""
    ready: bool = Field(
        ...,
        description="Overall readiness status"
    )
    checks: Dict[str, ReadinessCheck] = Field(
        default_factory=dict,
        description="Individual readiness checks"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Readiness check timestamp"
    )
    total_check_time_ms: Annotated[int, Field(ge=0)] = Field(
        ...,
        description="Total time for all checks"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional readiness details"
    )
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    @model_validator(mode='after')
    def calculate_readiness(self) -> 'ReadinessResponse':
        """Calculate overall readiness from individual checks."""
        if not self.checks:
            self.ready = False
            return self
            
        # Check all required checks pass
        required_checks = [c for c in self.checks.values() if c.required]
        self.ready = all(c.status == "pass" for c in required_checks)
        
        # Calculate total time
        self.total_check_time_ms = sum(c.duration_ms for c in self.checks.values())
        
        return self


class MetricsResponse(BaseModel):
    """Prometheus-compatible metrics response."""
    metrics: List[Dict[str, Any]] = Field(
        ...,
        description="List of metrics in Prometheus format"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Metrics collection timestamp"
    )
    
    def to_prometheus_format(self) -> str:
        """Convert to Prometheus text format."""
        lines = []
        for metric in self.metrics:
            # HELP line
            if 'help' in metric:
                lines.append(f"# HELP {metric['name']} {metric['help']}")
            # TYPE line
            if 'type' in metric:
                lines.append(f"# TYPE {metric['name']} {metric['type']}")
            # Metric lines
            for sample in metric.get('samples', []):
                labels = ','.join(f'{k}="{v}"' for k, v in sample.get('labels', {}).items())
                if labels:
                    lines.append(f"{metric['name']}{{{labels}}} {sample['value']}")
                else:
                    lines.append(f"{metric['name']} {sample['value']}")
        
        return '\n'.join(lines)


class ConfigurationValidationResult(BaseModel):
    """Configuration validation result."""
    valid: bool = Field(
        ...,
        description="Whether configuration is valid"
    )
    errors: List[Dict[str, Any]] = Field(
        default_factory=list,
        max_items=100,
        description="Configuration errors found"
    )
    warnings: List[Dict[str, Any]] = Field(
        default_factory=list,
        max_items=100,
        description="Configuration warnings"
    )
    config_version: str = Field(
        ...,
        pattern=r'^\d+\.\d+\.\d+$',
        description="Configuration version validated"
    )
    validation_time_ms: Annotated[int, Field(ge=0)] = Field(
        ...,
        description="Validation execution time"
    )
    validated_sections: List[str] = Field(
        default_factory=list,
        description="Configuration sections validated"
    )


class ConfigurationReloadResponse(BaseModel):
    """Response from configuration reload."""
    success: bool = Field(
        ...,
        description="Whether reload was successful"
    )
    validation_result: ConfigurationValidationResult = Field(
        ...,
        description="Validation results"
    )
    applied_changes: Dict[str, Any] = Field(
        default_factory=dict,
        description="Changes that were applied"
    )
    rolled_back: bool = Field(
        False,
        description="Whether changes were rolled back"
    )
    reload_time_ms: Annotated[int, Field(ge=0)] = Field(
        ...,
        description="Time taken to reload configuration"
    )