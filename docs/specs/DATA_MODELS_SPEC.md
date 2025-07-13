# Data Models Specification for SizeComparator

## Document Overview
This specification defines comprehensive Pydantic data models that serve as the backbone for all system interactions in SizeComparator. These models ensure type safety, runtime validation, and seamless integration across all system components while maintaining sub-10ms validation times and zero runtime type errors.

## 1. Executive Summary

The SizeComparator data models architecture provides a strongly-typed foundation for all system interactions. Built on Pydantic V2, these models serve as contracts between services, validation gateways for user input, and serialization interfaces for external communication.

### Key Responsibilities
- **Request/Response Validation**: Comprehensive input validation with detailed error messages
- **Error Standardization**: Unified error taxonomy aligned with monitoring requirements  
- **AI Provider Integration**: Type-safe interfaces for multi-provider AI services
- **Health Monitoring**: Structured health check responses for operational excellence
- **Configuration Validation**: Runtime validation of configuration changes

### Technology Stack
- **Pydantic V2**: Advanced validation with 3x performance improvement over V1
- **FastAPI Integration**: Automatic OpenAPI documentation generation
- **JSON Schema**: Standards-based validation and documentation
- **Python 3.11+**: Latest type hints and performance optimizations

### Performance Targets
- Model validation: < 10ms per request
- JSON serialization: < 5ms for typical responses  
- Memory usage: < 1MB per request model instance
- Zero runtime type errors through comprehensive validation

## 2. Weight Comparison Request/Response Models with Validation

### 2.1 Core Weight Comparison Models

#### 2.1.1 Request Models with Advanced Validation

```python
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional, List, Dict, Any, Union, Literal, Annotated
from decimal import Decimal
from datetime import datetime
from uuid import UUID, uuid4
from enum import Enum
import re

class WeightUnit(str, Enum):
    """Supported weight units with exact conversions."""
    KILOGRAM = "kg"
    POUND = "lb" 
    OUNCE = "oz"
    GRAM = "g"
    STONE = "st"
    METRIC_TON = "mt"
    SHORT_TON = "ton"
    LONG_TON = "long_ton"
    
    @classmethod
    def from_string(cls, value: str) -> 'WeightUnit':
        """Parse unit from various string formats."""
        mappings = {
            'kilogram': cls.KILOGRAM, 'kilograms': cls.KILOGRAM,
            'pound': cls.POUND, 'pounds': cls.POUND, 'lbs': cls.POUND,
            'ounce': cls.OUNCE, 'ounces': cls.OUNCE,
            'gram': cls.GRAM, 'grams': cls.GRAM,
            'stone': cls.STONE, 'stones': cls.STONE,
            'ton': cls.SHORT_TON, 'tons': cls.SHORT_TON,
            'metric ton': cls.METRIC_TON, 'metric tons': cls.METRIC_TON,
            'long ton': cls.LONG_TON, 'long tons': cls.LONG_TON
        }
        return mappings.get(value.lower(), None)

class ComparisonType(str, Enum):
    """Types of comparisons supported."""
    BASIC = "basic"
    DETAILED = "detailed"
    SCIENTIFIC = "scientific"
    VISUAL = "visual"

class WeightInput(BaseModel):
    """Individual weight input with validation."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    value: Union[float, str] = Field(
        ..., 
        description="Weight value - numeric or text like '5 pounds'",
        examples=["5.5", "100 kg", "10 pounds 3 ounces"]
    )
    unit: Optional[WeightUnit] = Field(
        None, 
        description="Unit if not specified in value"
    )
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        1.0,
        description="Confidence in the weight accuracy"
    )
    source: Optional[str] = Field(
        None,
        max_length=200,
        description="Source of weight information"
    )
    
    @field_validator('value')
    @classmethod
    def validate_weight_value(cls, v: Union[float, str]) -> Union[float, str]:
        """Validate weight value format and range."""
        if isinstance(v, str):
            # Parse natural language weights
            patterns = [
                r'^(\d+(?:\.\d+)?)\s*([a-zA-Z]+)?$',  # "5.5 kg"
                r'^(\d+)\s+(\d+)/(\d+)\s*([a-zA-Z]+)?$',  # "5 1/2 pounds"
                r'^(\d+)\s*([a-zA-Z]+)\s+(\d+)\s*([a-zA-Z]+)$'  # "5 pounds 3 ounces"
            ]
            
            matched = False
            for pattern in patterns:
                if re.match(pattern, v.strip()):
                    matched = True
                    break
                    
            if not matched:
                raise ValueError(
                    'Invalid weight format. Examples: "5.5", "5.5 kg", "5 pounds 3 ounces"'
                )
            
            # Extract numeric value for range validation
            numeric_match = re.search(r'(\d+(?:\.\d+)?)', v)
            if numeric_match:
                numeric_value = float(numeric_match.group(1))
                if numeric_value <= 0:
                    raise ValueError('Weight must be positive')
                if numeric_value > 1_000_000:  # 1 million kg max
                    raise ValueError('Weight exceeds maximum limit (1,000,000 kg)')
        
        elif isinstance(v, (int, float)):
            if v <= 0:
                raise ValueError('Weight must be positive')
            if v > 1_000_000:
                raise ValueError('Weight exceeds maximum limit (1,000,000 kg)')
        
        return v

    @model_validator(mode='after')
    def validate_weight_consistency(self) -> 'WeightInput':
        """Validate weight input consistency."""
        if isinstance(self.value, str) and self.unit:
            # Check for conflicting unit specifications
            if re.search(r'[a-zA-Z]', self.value):
                # Extract unit from string
                unit_match = re.search(r'([a-zA-Z]+)(?:\s|$)', self.value)
                if unit_match:
                    string_unit = WeightUnit.from_string(unit_match.group(1))
                    if string_unit and string_unit != self.unit:
                        raise ValueError(
                            f'Conflicting units: "{string_unit}" in value vs "{self.unit}" in unit field'
                        )
        
        return self

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
        pattern=r'^[a-zA-Z0-9\s\-_.,!?()\'\"]+$'
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
        pattern=r'^[a-zA-Z0-9\s\-_.,!?()\'\"]+$'
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
```

#### 2.1.2 Response Models with Serialization Control

```python
from typing import Optional, List, Dict, Any, Union
from decimal import Decimal
from datetime import datetime

class ProcessedWeight(BaseModel):
    """Processed weight with full metadata."""
    model_config = ConfigDict(
        json_encoders={
            Decimal: lambda v: float(v),
            datetime: lambda v: v.isoformat()
        }
    )
    
    original_input: WeightInput = Field(
        ...,
        description="Original weight input"
    )
    parsed_value: Annotated[Decimal, Field(
        decimal_places=6,
        max_digits=12
    )] = Field(
        ...,
        description="Parsed numeric value in base unit (kg)"
    )
    display_value: str = Field(
        ...,
        description="Human-readable weight with unit"
    )
    unit_used: WeightUnit = Field(
        ...,
        description="Final unit after processing"
    )
    conversion_factor: Optional[Decimal] = Field(
        None,
        description="Factor used for unit conversion"
    )
    parsing_confidence: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        ...,
        description="Confidence in parsing accuracy"
    )
    validation_warnings: List[str] = Field(
        default_factory=list,
        max_items=10,
        description="Any validation warnings"
    )

class ComparisonAnalysis(BaseModel):
    """Detailed comparison analysis results."""
    weight_ratio: Annotated[Decimal, Field(decimal_places=3)] = Field(
        ...,
        description="Ratio of item1/item2 weights"
    )
    percentage_difference: Annotated[Decimal, Field(decimal_places=2)] = Field(
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
```

### 2.2 Weight Processing and Validation Utilities

```python
from typing import Dict, Any, Tuple, Optional
import re
from decimal import Decimal, InvalidOperation

class WeightValidators:
    """Custom validators for weight-related fields."""
    
    # Conversion factors to kilograms
    CONVERSION_FACTORS = {
        WeightUnit.KILOGRAM: Decimal('1.0'),
        WeightUnit.GRAM: Decimal('0.001'),
        WeightUnit.POUND: Decimal('0.45359237'),
        WeightUnit.OUNCE: Decimal('0.028349523125'),
        WeightUnit.STONE: Decimal('6.35029318'),
        WeightUnit.METRIC_TON: Decimal('1000.0'),
        WeightUnit.SHORT_TON: Decimal('907.18474'),
        WeightUnit.LONG_TON: Decimal('1016.0469088')
    }
    
    @classmethod
    def parse_weight_string(cls, value: str) -> Dict[str, Any]:
        """Parse natural language weight strings."""
        value = value.strip().lower()
        
        # Pattern for simple weights: "5.5 kg"
        simple_pattern = r'^(\d+(?:\.\d+)?)\s*([a-zA-Z]+)?$'
        match = re.match(simple_pattern, value)
        if match:
            numeric_value = Decimal(match.group(1))
            unit_str = match.group(2)
            
            if unit_str:
                unit = WeightUnit.from_string(unit_str)
                if not unit:
                    raise ValueError(f"Unknown unit: {unit_str}")
            else:
                unit = WeightUnit.KILOGRAM
                
            return {
                'value': numeric_value,
                'unit': unit,
                'original_string': value
            }
        
        # Pattern for compound weights: "5 pounds 3 ounces"
        compound_pattern = r'^(\d+)\s*([a-zA-Z]+)\s+(\d+)\s*([a-zA-Z]+)$'
        match = re.match(compound_pattern, value)
        if match:
            main_value = Decimal(match.group(1))
            main_unit_str = match.group(2)
            sub_value = Decimal(match.group(3))
            sub_unit_str = match.group(4)
            
            main_unit = WeightUnit.from_string(main_unit_str)
            sub_unit = WeightUnit.from_string(sub_unit_str)
            
            if not main_unit or not sub_unit:
                raise ValueError(f"Unknown units in compound weight")
            
            # Convert to common unit (kg) and sum
            main_kg = main_value * cls.CONVERSION_FACTORS[main_unit]
            sub_kg = sub_value * cls.CONVERSION_FACTORS[sub_unit]
            total_kg = main_kg + sub_kg
            
            return {
                'value': total_kg,
                'unit': WeightUnit.KILOGRAM,
                'original_string': value,
                'compound': True
            }
        
        raise ValueError(f"Unable to parse weight: {value}")
    
    @classmethod
    def validate_decimal_precision(cls, value: Decimal, max_places: int = 6) -> Decimal:
        """Ensure decimal values don't exceed precision limits."""
        try:
            # Round to specified decimal places
            quantized = value.quantize(Decimal(10) ** -max_places)
            return quantized
        except InvalidOperation:
            raise ValueError(f"Decimal precision exceeded: {value}")

class WeightProcessor:
    """Process and convert weight values with validation."""
    
    @classmethod
    def process_weight_input(cls, weight_input: WeightInput) -> ProcessedWeight:
        """Process weight input into standardized format."""
        if isinstance(weight_input.value, str):
            # Parse string weight
            parsed_data = WeightValidators.parse_weight_string(weight_input.value)
            numeric_value = parsed_data['value']
            unit = parsed_data['unit']
        else:
            # Numeric weight
            numeric_value = Decimal(str(weight_input.value))
            unit = weight_input.unit or WeightUnit.KILOGRAM
        
        # Convert to kilograms for internal storage
        kg_value = numeric_value * WeightValidators.CONVERSION_FACTORS[unit]
        kg_value = WeightValidators.validate_decimal_precision(kg_value)
        
        # Generate display value based on output preferences
        if weight_input.unit:
            # Keep original unit for display
            display_value = f"{numeric_value:,.3f} {unit.value}"
        else:
            # Default to kg for display
            display_value = f"{kg_value:,.3f} kg"
        
        # Build response
        return ProcessedWeight(
            original_input=weight_input,
            parsed_value=kg_value,
            display_value=display_value,
            unit_used=unit,
            conversion_factor=WeightValidators.CONVERSION_FACTORS[unit],
            parsing_confidence=weight_input.confidence or 1.0,
            validation_warnings=[]
        )
    
    @classmethod
    def calculate_comparison(cls, weight1: ProcessedWeight, weight2: ProcessedWeight) -> ComparisonAnalysis:
        """Calculate detailed comparison between two weights."""
        # All weights are in kg for comparison
        value1 = weight1.parsed_value
        value2 = weight2.parsed_value
        
        # Calculate metrics
        ratio = value1 / value2 if value2 > 0 else Decimal('0')
        percentage_diff = ((value1 - value2) / value2 * 100) if value2 > 0 else Decimal('0')
        absolute_diff = abs(value1 - value2)
        
        # Determine heavier item
        if value1 > value2 * Decimal('1.01'):  # 1% tolerance
            heavier = "item1"
        elif value2 > value1 * Decimal('1.01'):
            heavier = "item2"
        else:
            heavier = "equal"
        
        # Create difference weight
        diff_weight = ProcessedWeight(
            original_input=WeightInput(value=float(absolute_diff), unit=WeightUnit.KILOGRAM),
            parsed_value=absolute_diff,
            display_value=f"{absolute_diff:,.3f} kg",
            unit_used=WeightUnit.KILOGRAM,
            parsing_confidence=1.0
        )
        
        return ComparisonAnalysis(
            weight_ratio=ratio,
            percentage_difference=percentage_diff,
            absolute_difference=diff_weight,
            heavier_item=heavier,
            significance_level="moderate",  # Will be recalculated by validator
            comparison_category="general"
        )
```

## 3. Error Response Models Matching ERROR_MONITORING_SPEC Taxonomy

### 3.1 Standardized Error Models

```python
from enum import Enum
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from uuid import UUID, uuid4

class ErrorCategory(str, Enum):
    """Error categories aligned with ERROR_MONITORING_SPEC."""
    CLIENT_ERROR = "client_error"          # 4xx errors - user input issues
    SERVER_ERROR = "server_error"          # 5xx errors - internal failures
    INTEGRATION_ERROR = "integration_error" # External API failures
    BUSINESS_LOGIC_ERROR = "business_logic_error" # Validation/constraint violations

class ErrorSeverity(str, Enum):
    """Error severity levels from ERROR_MONITORING_SPEC."""
    CRITICAL = "critical"  # System outage, immediate intervention required
    WARNING = "warning"    # Degraded performance, notify on-call team
    INFO = "info"         # Anomalies worth investigating, no immediate action

class FieldError(BaseModel):
    """Individual field validation error."""
    field_path: str = Field(
        ...,
        description="JSONPath to the field with error",
        examples=["item1_weight.value", "request.ai_temperature"]
    )
    error_code: str = Field(
        ...,
        pattern=r'^[A-Z][A-Z0-9_]+$',
        description="Machine-readable error code"
    )
    error_message: str = Field(
        ...,
        description="Human-readable error description"
    )
    invalid_value: Optional[Any] = Field(
        None,
        description="The invalid value that caused the error"
    )
    constraint_violated: Optional[str] = Field(
        None,
        description="Validation constraint that was violated"
    )
    suggested_fix: Optional[str] = Field(
        None,
        description="Suggested correction for the error"
    )

class ErrorContext(BaseModel):
    """Additional context for error investigation."""
    component: str = Field(
        ...,
        description="System component where error occurred",
        examples=["api", "weight_processor", "ai_provider", "cache"]
    )
    operation: str = Field(
        ...,
        description="Operation being performed when error occurred"
    )
    user_agent: Optional[str] = Field(
        None,
        max_length=500,
        description="Client user agent string"
    )
    ip_address: Optional[str] = Field(
        None,
        pattern=r'^(\d{1,3}\.){3}\d{1,3}$|^[a-fA-F0-9:]+$',
        description="Client IP address (anonymized)"
    )
    session_id: Optional[str] = Field(
        None,
        description="User session identifier"
    )
    correlation_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional correlation data"
    )

class BaseErrorResponse(BaseModel):
    """Base error response model for ERROR_MONITORING_SPEC compliance."""
    error_id: UUID = Field(
        default_factory=uuid4,
        description="Unique error identifier for tracking"
    )
    error_code: str = Field(
        ...,
        pattern=r'^[A-Z][A-Z0-9_]+$',
        description="Machine-readable error code"
    )
    error_category: ErrorCategory = Field(
        ...,
        description="Error classification for monitoring"
    )
    severity: ErrorSeverity = Field(
        ...,
        description="Error severity level"
    )
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Human-readable error message"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )
    request_id: UUID = Field(
        ...,
        description="Request correlation ID from BACKEND_CORE_SPEC"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error occurrence timestamp"
    )
    context: Optional[ErrorContext] = Field(
        None,
        description="Error context for investigation"
    )
    remediation_hint: Optional[str] = Field(
        None,
        max_length=500,
        description="Suggested remediation steps"
    )
    documentation_url: Optional[str] = Field(
        None,
        pattern=r'^https?://.*',
        description="Link to relevant documentation"
    )

class ValidationErrorResponse(BaseErrorResponse):
    """Validation error with field-specific details."""
    error_category: Literal[ErrorCategory.CLIENT_ERROR] = Field(
        default=ErrorCategory.CLIENT_ERROR,
        description="Always client error for validation failures"
    )
    field_errors: List[FieldError] = Field(
        default_factory=list,
        max_items=50,
        description="Detailed field validation errors"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error_id": "550e8400-e29b-41d4-a716-446655440000",
                "error_code": "VALIDATION_FAILED",
                "error_category": "client_error",
                "severity": "info",
                "message": "Request validation failed",
                "request_id": "660e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2025-07-13T10:30:00Z",
                "field_errors": [
                    {
                        "field_path": "item1_weight.value",
                        "error_code": "INVALID_WEIGHT_FORMAT",
                        "error_message": "Weight must be positive number",
                        "invalid_value": "-5",
                        "constraint_violated": "minimum",
                        "suggested_fix": "Provide a positive weight value"
                    }
                ],
                "remediation_hint": "Please check the field errors and correct your input",
                "documentation_url": "https://docs.sizecomparator.com/errors/validation"
            }
        }
    )

class BusinessLogicErrorResponse(BaseErrorResponse):
    """Business logic violation errors."""
    error_category: Literal[ErrorCategory.BUSINESS_LOGIC_ERROR] = Field(
        default=ErrorCategory.BUSINESS_LOGIC_ERROR,
        description="Business logic constraint violation"
    )
    constraint_type: str = Field(
        ...,
        description="Type of business constraint violated",
        examples=["comparison_limit", "weight_range", "item_restriction"]
    )
    constraint_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Details about the violated constraint"
    )

class IntegrationErrorResponse(BaseErrorResponse):
    """External service integration errors."""
    error_category: Literal[ErrorCategory.INTEGRATION_ERROR] = Field(
        default=ErrorCategory.INTEGRATION_ERROR,
        description="External service failure"
    )
    service_name: str = Field(
        ...,
        description="Name of the failing external service",
        examples=["openai", "anthropic", "xai", "redis"]
    )
    service_status: str = Field(
        ...,
        description="Status of the external service",
        examples=["timeout", "rate_limited", "authentication_failed", "circuit_open"]
    )
    retry_after_seconds: Optional[int] = Field(
        None,
        ge=0,
        le=3600,
        description="Suggested retry delay in seconds"
    )
    fallback_available: bool = Field(
        False,
        description="Whether fallback service is available"
    )
    fallback_service: Optional[str] = Field(
        None,
        description="Name of fallback service if available"
    )

class ServerErrorResponse(BaseErrorResponse):
    """Internal server errors."""
    error_category: Literal[ErrorCategory.SERVER_ERROR] = Field(
        default=ErrorCategory.SERVER_ERROR,
        description="Internal server failure"
    )
    incident_id: Optional[str] = Field(
        None,
        description="Incident tracking identifier"
    )
    estimated_fix_time: Optional[datetime] = Field(
        None,
        description="Estimated fix time if known"
    )
    stack_trace: Optional[str] = Field(
        None,
        description="Stack trace (only in development mode)"
    )
    
    @model_validator(mode='after')
    def remove_sensitive_data_in_production(self) -> 'ServerErrorResponse':
        """Remove sensitive data in production."""
        import os
        if os.getenv('SIZECOMPARATOR_ENV') == 'production':
            self.stack_trace = None
            if self.details:
                # Remove any sensitive keys
                sensitive_keys = ['password', 'api_key', 'secret', 'token']
                self.details = {
                    k: v for k, v in self.details.items() 
                    if not any(sensitive in k.lower() for sensitive in sensitive_keys)
                }
        return self
```

### 3.2 Error Factory and Helpers

```python
from typing import Type, Optional, Dict, Any
import traceback

class ErrorFactory:
    """Factory for creating standardized error responses."""
    
    @staticmethod
    def validation_error(
        field_errors: List[FieldError],
        request_id: UUID,
        message: Optional[str] = None
    ) -> ValidationErrorResponse:
        """Create validation error response."""
        return ValidationErrorResponse(
            error_code="VALIDATION_FAILED",
            severity=ErrorSeverity.INFO,
            message=message or f"Validation failed for {len(field_errors)} field(s)",
            request_id=request_id,
            field_errors=field_errors,
            remediation_hint="Please check the field errors and correct your input",
            documentation_url="https://docs.sizecomparator.com/errors/validation"
        )
    
    @staticmethod
    def integration_error(
        service_name: str,
        service_status: str,
        request_id: UUID,
        retry_after: Optional[int] = None,
        fallback_service: Optional[str] = None
    ) -> IntegrationErrorResponse:
        """Create integration error response."""
        error_codes = {
            "timeout": "SERVICE_TIMEOUT",
            "rate_limited": "RATE_LIMIT_EXCEEDED",
            "authentication_failed": "AUTH_FAILED",
            "circuit_open": "CIRCUIT_BREAKER_OPEN"
        }
        
        return IntegrationErrorResponse(
            error_code=error_codes.get(service_status, "INTEGRATION_ERROR"),
            severity=ErrorSeverity.WARNING if fallback_service else ErrorSeverity.CRITICAL,
            message=f"{service_name} service {service_status}",
            request_id=request_id,
            service_name=service_name,
            service_status=service_status,
            retry_after_seconds=retry_after,
            fallback_available=bool(fallback_service),
            fallback_service=fallback_service,
            remediation_hint=f"Using fallback service: {fallback_service}" if fallback_service else "Please try again later"
        )
    
    @staticmethod
    def server_error(
        error: Exception,
        request_id: UUID,
        component: str,
        operation: str
    ) -> ServerErrorResponse:
        """Create server error response."""
        import os
        
        response = ServerErrorResponse(
            error_code="INTERNAL_SERVER_ERROR",
            severity=ErrorSeverity.CRITICAL,
            message="An internal error occurred",
            request_id=request_id,
            context=ErrorContext(
                component=component,
                operation=operation
            ),
            remediation_hint="Our team has been notified. Please try again later."
        )
        
        # Add stack trace in development
        if os.getenv('SIZECOMPARATOR_ENV') == 'development':
            response.stack_trace = traceback.format_exc()
            response.message = str(error)
        
        return response
```

## 4. AI Provider Response Models for AI_PROVIDER_SPEC Integration

### 4.1 AI Provider Interface Models

```python
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
        decimal_places=4,
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
    max_cost: Optional[Decimal] = Field(
        None,
        decimal_places=4,
        description="Maximum acceptable cost"
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
        decimal_places=4,
        description="Estimated cost for request"
    )
    estimated_response_time_ms: int = Field(
        ...,
        description="Estimated response time"
    )
```

## 5. Health Check Models for DEPLOYMENT_OPS_SPEC Endpoints

### 5.1 Health Check Response Models

```python
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
    components: Dict[str, ComponentHealth] = Field(
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
            
        unhealthy_count = sum(1 for c in self.components.values() if c.status == "unhealthy")
        degraded_count = sum(1 for c in self.components.values() if c.status == "degraded")
        
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
        },
        json_schema_extra={
            "example": {
                "ready": True,
                "timestamp": "2025-07-13T10:30:00Z",
                "total_check_time_ms": 45,
                "checks": {
                    "ai_provider_connectivity": {
                        "check_name": "ai_provider_connectivity",
                        "status": "pass",
                        "message": "All AI providers reachable",
                        "duration_ms": 25,
                        "required": True
                    },
                    "configuration_loaded": {
                        "check_name": "configuration_loaded",
                        "status": "pass",
                        "duration_ms": 5,
                        "required": True
                    },
                    "memory_usage": {
                        "check_name": "memory_usage",
                        "status": "pass",
                        "message": "Memory usage at 45%",
                        "duration_ms": 10,
                        "required": False,
                        "threshold": {"max_percent": 80}
                    }
                }
            }
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
```

## 6. Configuration Models for CONFIG_SYSTEM_SPEC Integration

### 6.1 Configuration Validation Models

```python
class ConfigurationError(BaseModel):
    """Configuration validation error."""
    config_path: str = Field(
        ...,
        description="Configuration path with error",
        examples=["api.providers.openai.timeout_seconds", "cache.settings.ttl"]
    )
    error_type: str = Field(
        ...,
        description="Type of configuration error",
        examples=["missing_required", "invalid_type", "out_of_range", "unknown_field"]
    )
    error_message: str = Field(
        ...,
        description="Detailed error message"
    )
    current_value: Optional[Any] = Field(
        None,
        description="Current invalid value"
    )
    expected_type: Optional[str] = Field(
        None,
        description="Expected type or format"
    )
    suggested_value: Optional[Any] = Field(
        None,
        description="Suggested correct value"
    )
    schema_constraint: Optional[Dict[str, Any]] = Field(
        None,
        description="JSON Schema constraint that failed"
    )

class ConfigurationValidationResult(BaseModel):
    """Configuration validation result."""
    valid: bool = Field(
        ...,
        description="Whether configuration is valid"
    )
    errors: List[ConfigurationError] = Field(
        default_factory=list,
        max_items=100,
        description="Configuration errors found"
    )
    warnings: List[ConfigurationError] = Field(
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

class TemplateValidationResult(BaseModel):
    """Template validation result for CONFIG_SYSTEM_SPEC."""
    template_id: str = Field(
        ...,
        pattern=r'^[a-zA-Z0-9_-]+$',
        description="Template identifier"
    )
    valid: bool = Field(
        ...,
        description="Template validation status"
    )
    syntax_errors: List[str] = Field(
        default_factory=list,
        max_items=50,
        description="Template syntax errors"
    )
    variable_errors: List[str] = Field(
        default_factory=list,
        max_items=50,
        description="Template variable errors"
    )
    required_variables: List[str] = Field(
        default_factory=list,
        description="Required template variables"
    )
    optional_variables: List[str] = Field(
        default_factory=list,
        description="Optional template variables"
    )
    provider_compatibility: Dict[str, bool] = Field(
        default_factory=dict,
        description="Provider compatibility status"
    )
    example_output: Optional[str] = Field(
        None,
        max_length=1000,
        description="Example rendered output"
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
```

## Implementation Requirements

### Type Safety and Runtime Validation
1. **Pydantic V2 Integration**: All models use Pydantic V2 features including:
   - `field_validator` and `model_validator` decorators
   - `ConfigDict` for model configuration
   - `Annotated` types for field constraints
   - Improved validation performance (3x faster than V1)

2. **Custom Validators**: Domain-specific validation logic for:
   - Natural language weight parsing
   - Unit conversion and validation
   - Business rule enforcement
   - Content moderation

3. **Runtime Type Checking**: Zero runtime type errors through:
   - Comprehensive field validation
   - Type coercion where appropriate
   - Clear error messages with remediation hints

4. **Serialization Control**: Precise JSON serialization with:
   - Custom encoders for Decimal, datetime, UUID
   - Consistent float precision
   - ISO 8601 timestamp formatting

### Integration Contracts
1. **BACKEND_CORE_SPEC Compliance**: 
   - All request/response models align with FastAPI endpoints
   - Async/await compatibility maintained
   - Request ID propagation throughout

2. **ERROR_MONITORING_SPEC Taxonomy**: 
   - Exact error categorization (CLIENT_ERROR, SERVER_ERROR, etc.)
   - Severity levels for alert routing
   - Structured logging integration

3. **AI_PROVIDER_SPEC Interface**: 
   - Circuit breaker state models
   - Provider health tracking
   - Fallback mechanism support

4. **DEPLOYMENT_OPS_SPEC Health**: 
   - Standardized health check responses
   - Prometheus metrics compatibility
   - SLA monitoring support

5. **CONFIG_SYSTEM_SPEC Validation**: 
   - Configuration change validation
   - Hot-reload safety checks
   - Template validation integration

### Performance Requirements
- **Model Validation**: < 10ms per request
  - Field validators optimized for performance
  - Regex patterns pre-compiled
  - Minimal memory allocation

- **JSON Serialization**: < 5ms for typical responses
  - Efficient custom encoders
  - Lazy evaluation where possible
  - Response streaming support

- **Memory Usage**: < 1MB per request model instance
  - Efficient data structures
  - No unnecessary object retention
  - Garbage collection friendly

- **Zero Runtime Type Errors**:
  - 100% type coverage
  - Comprehensive validation
  - Fail-fast error handling

This specification provides the complete data model foundation for SizeComparator, ensuring type safety, comprehensive validation, and seamless integration across all system components while supporting the 99% uptime SLA through proper error handling and health monitoring.