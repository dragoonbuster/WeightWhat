"""
Request models for SizeComparator API endpoints.

This module contains all request models for weight comparisons and related operations
as specified in the DATA_MODELS_SPEC.
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional, List, Dict, Any, Union, Literal, Annotated
from datetime import datetime
from uuid import UUID, uuid4
import re

from .weight import WeightInput, WeightUnit, ComparisonType


class WeightComparisonRequest(BaseModel):
    """Primary request model for weight comparisons."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid',
        json_schema_extra={
            "example": {
                "item1": "African Elephant",
                "item1_weight": {
                    "value": "5000 kg",
                    "confidence": 0.95,
                    "source": "Wildlife Conservation Society"
                },
                "item2": "Tesla Model 3",
                "item2_weight": {
                    "value": 1611,
                    "unit": "kg",
                    "confidence": 1.0,
                    "source": "Tesla Specifications"
                },
                "output_unit": "kg",
                "comparison_type": "detailed",
                "include_visualization": True,
                "preferred_provider": "auto"
            }
        }
    )
    
    item1: Annotated[str, Field(
        min_length=1, 
        max_length=200,
        pattern=r'^[a-zA-Z0-9\s\-_.,!?()\'\\"]+$'
    )] = Field(
        ...,
        description="First item to compare"
    )
    item1_weight: WeightInput = Field(
        ...,
        description="Weight specification for first item"
    )
    item2: Annotated[str, Field(
        min_length=1, 
        max_length=200,
        pattern=r'^[a-zA-Z0-9\s\-_.,!?()\'\\"]+$'
    )] = Field(
        ...,
        description="Second item to compare"
    )
    item2_weight: WeightInput = Field(
        ...,
        description="Weight specification for second item"
    )
    
    # Output preferences
    output_unit: Optional[WeightUnit] = Field(
        None,
        description="Preferred unit for results"
    )
    comparison_type: ComparisonType = Field(
        ComparisonType.BASIC,
        description="Type of comparison analysis"
    )
    include_visualization: bool = Field(
        True,
        description="Generate AI visualization prompt"
    )
    locale: Optional[str] = Field(
        "en-US",
        pattern=r'^[a-z]{2}-[A-Z]{2}$',
        description="Locale for number formatting"
    )
    
    # AI Provider preferences (AI_PROVIDER_SPEC integration)
    preferred_provider: Optional[Literal["openai", "anthropic", "xai", "auto"]] = Field(
        "auto",
        description="Preferred AI provider or 'auto' for system selection"
    )
    ai_temperature: Annotated[float, Field(ge=0.0, le=2.0)] = Field(
        0.7,
        description="AI generation temperature"
    )
    max_response_tokens: Annotated[int, Field(ge=50, le=2000)] = Field(
        500,
        description="Maximum tokens for AI response"
    )
    
    # Request metadata
    request_id: UUID = Field(
        default_factory=uuid4,
        description="Unique request identifier"
    )
    client_version: Optional[str] = Field(
        None,
        pattern=r'^\d+\.\d+\.\d+$',
        description="Client application version"
    )
    user_preferences: Optional[Dict[str, Any]] = Field(
        None,
        description="User-specific preferences"
    )
    
    @model_validator(mode='after')
    def validate_comparison_logic(self) -> 'WeightComparisonRequest':
        """Business logic validation for comparison requests."""
        # Prevent identical items
        if self.item1.lower().strip() == self.item2.lower().strip():
            raise ValueError('Cannot compare identical items')
        
        # Validate inappropriate content
        inappropriate_patterns = [
            r'\b(weapon|bomb|explosive)\b',
            r'\b(drug|narcotic|illegal)\b',
            r'\b(dead|corpse|body)\b'
        ]
        
        for pattern in inappropriate_patterns:
            if re.search(pattern, self.item1, re.IGNORECASE) or \
               re.search(pattern, self.item2, re.IGNORECASE):
                raise ValueError('Inappropriate content detected')
        
        return self


class ProviderSelectionRequest(BaseModel):
    """Request for provider selection logic."""
    preferred_provider: Optional[str] = Field(
        None,
        description="User's preferred provider"
    )
    excluded_providers: List[str] = Field(
        default_factory=list,
        description="Providers to exclude"
    )
    require_high_confidence: bool = Field(
        False,
        description="Whether high confidence is required"
    )
    max_cost: Optional[float] = Field(
        None,
        description="Maximum acceptable cost"
    )


class ConfigurationReloadRequest(BaseModel):
    """Request to reload configuration."""
    config_sections: Optional[List[str]] = Field(
        None,
        description="Specific sections to reload, None for all"
    )
    validate_only: bool = Field(
        False,
        description="Only validate without applying"
    )
    rollback_on_error: bool = Field(
        True,
        description="Rollback to previous config on error"
    )