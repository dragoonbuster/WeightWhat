"""
Core weight models and enums for SizeComparator.

This module contains all weight-related models including units, input validation,
and processing utilities as specified in the DATA_MODELS_SPEC.
"""

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional, List, Dict, Any, Union, Literal, Annotated
from decimal import Decimal, InvalidOperation
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
    def from_string(cls, value: str) -> Optional['WeightUnit']:
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
    parsed_value: Decimal = Field(
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
    def calculate_comparison(cls, weight1: 'ProcessedWeight', weight2: 'ProcessedWeight') -> Dict[str, Any]:
        """Calculate detailed comparison between two weights."""
        from decimal import Decimal
        
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
        
        return {
            'weight_ratio': ratio,
            'percentage_difference': percentage_diff,
            'absolute_difference': diff_weight,
            'heavier_item': heavier,
            'significance_level': cls._determine_significance(ratio),
            'comparison_category': "general"
        }
    
    @staticmethod
    def _determine_significance(ratio: Decimal) -> str:
        """Determine significance level based on weight ratio."""
        ratio_float = float(ratio)
        
        if abs(ratio_float - 1) < 0.01:
            return "negligible"
        elif ratio_float < 2:
            return "small"
        elif ratio_float < 10:
            return "moderate"
        elif ratio_float < 100:
            return "large"
        else:
            return "extreme"