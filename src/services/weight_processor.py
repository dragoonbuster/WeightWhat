"""
Weight Processing Engine for SizeComparator

Comprehensive weight processing logic with precision, validation, unit conversion,
and seamless integration with all system components. Uses Decimal arithmetic
for high-precision calculations and provides comprehensive error handling.
"""

import re
import time
from decimal import Decimal, ROUND_HALF_UP, getcontext, InvalidOperation
from enum import Enum
from typing import Optional, Union, Dict, Any, List, Protocol
from pydantic import BaseModel, Field, field_validator, ConfigDict
import logging
from dataclasses import dataclass

# Configure decimal precision for all calculations
getcontext().prec = 28
getcontext().rounding = ROUND_HALF_UP

logger = logging.getLogger(__name__)


class WeightUnit(str, Enum):
    """Supported weight units with precise conversion factors"""
    # Primary units
    KILOGRAM = "kg"
    POUND = "lb"
    
    # Secondary units
    GRAM = "g"
    OUNCE = "oz"
    STONE = "st"
    METRIC_TON = "mt"
    SHORT_TON = "ton"
    
    # Specialized units
    MILLIGRAM = "mg"
    MICROGRAM = "ug"


class ErrorCategory(str, Enum):
    """Error categories aligned with ERROR_MONITORING_SPEC"""
    CLIENT_ERROR = "client_error"
    BUSINESS_LOGIC_ERROR = "business_logic_error"
    INTERNAL_ERROR = "internal_error"


class ErrorSeverity(str, Enum):
    """Error severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IConfigurationService(Protocol):
    """Configuration service interface"""
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        ...


@dataclass
class SimpleConfig:
    """Simple configuration implementation for development"""
    def get(self, key: str, default: Any = None) -> Any:
        config_map = {
            "comparison.precision": 2,
            "validation.min_weight_kg": 0.0001,  # Allow down to 0.1mg
            "validation.max_weight_kg": 1000000,
        }
        return config_map.get(key, default)


class ValidationError(BaseModel):
    """Validation error aligned with ERROR_MONITORING_SPEC"""
    code: str = Field(..., pattern=r'^WEIGHT_\d{3}$')
    message: str = Field(..., min_length=1)
    category: ErrorCategory
    field: str
    remediation_hint: Optional[str] = None


class ValidationWarning(BaseModel):
    """Validation warning for non-critical issues"""
    code: str = Field(..., pattern=r'^WEIGHT_W\d{3}$')
    message: str = Field(..., min_length=1)
    field: str


class ValidationResult(BaseModel):
    """Validation result with comprehensive error reporting"""
    is_valid: bool
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[ValidationWarning] = Field(default_factory=list)
    parsed_value: Optional[Decimal] = None
    parsed_unit: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class WeightValidationRules:
    """Comprehensive validation rules with configurable thresholds"""
    
    # Range limits (configurable via CONFIG_SYSTEM_SPEC)
    MIN_WEIGHT_KG = Decimal('0.000001')      # 1 microgram
    MAX_WEIGHT_KG = Decimal('1000000000')    # 1 billion kg
    
    # Practical limits for AI comparisons
    PRACTICAL_MIN_KG = Decimal('0.001')      # 1 gram
    PRACTICAL_MAX_KG = Decimal('1000000')    # 1000 metric tons
    
    # Precision limits
    MAX_DECIMAL_PLACES = 6
    DISPLAY_DECIMAL_PLACES = 3
    
    # Input format validation patterns
    WEIGHT_PATTERNS = {
        'decimal_with_unit': r'^(-?\d+(?:\.\d+)?)\s*([a-zA-Z]+)$',
        'fraction_with_unit': r'^(-?\d+/\d+)\s*([a-zA-Z]+)$',
        'mixed_units': r'^(-?\d+)\s*([a-zA-Z]+)\s*(-?\d+(?:\.\d+)?)\s*([a-zA-Z]+)$',
        'scientific': r'^(-?\d+(?:\.\d+)?)[eE][+-]?\d+\s*([a-zA-Z]+)$',
        'range': r'^(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)\s*([a-zA-Z]+)$'
    }


class UnitValidator:
    """Validates and normalizes weight unit names"""
    
    UNIT_ALIASES = {
        # Kilogram aliases
        'kg': WeightUnit.KILOGRAM, 'kgs': WeightUnit.KILOGRAM,
        'kilogram': WeightUnit.KILOGRAM, 'kilograms': WeightUnit.KILOGRAM,
        'kilo': WeightUnit.KILOGRAM, 'kilos': WeightUnit.KILOGRAM,
        
        # Pound aliases
        'lb': WeightUnit.POUND, 'lbs': WeightUnit.POUND,
        'pound': WeightUnit.POUND, 'pounds': WeightUnit.POUND,
        '#': WeightUnit.POUND,
        
        # Gram aliases
        'g': WeightUnit.GRAM, 'gm': WeightUnit.GRAM, 'gms': WeightUnit.GRAM,
        'gram': WeightUnit.GRAM, 'grams': WeightUnit.GRAM,
        
        # Ounce aliases
        'oz': WeightUnit.OUNCE, 'ounce': WeightUnit.OUNCE, 'ounces': WeightUnit.OUNCE,
        
        # Stone aliases
        'st': WeightUnit.STONE, 'stone': WeightUnit.STONE, 'stones': WeightUnit.STONE,
        
        # Metric ton aliases
        'mt': WeightUnit.METRIC_TON, 'tonne': WeightUnit.METRIC_TON, 'tonnes': WeightUnit.METRIC_TON,
        'metric ton': WeightUnit.METRIC_TON, 'metric tons': WeightUnit.METRIC_TON,
        
        # Short ton aliases
        'ton': WeightUnit.SHORT_TON, 'tons': WeightUnit.SHORT_TON,
        'short ton': WeightUnit.SHORT_TON, 'short tons': WeightUnit.SHORT_TON,
        
        # Milligram aliases
        'mg': WeightUnit.MILLIGRAM, 'milligram': WeightUnit.MILLIGRAM, 'milligrams': WeightUnit.MILLIGRAM,
        
        # Microgram aliases
        'ug': WeightUnit.MICROGRAM, 'microgram': WeightUnit.MICROGRAM, 'micrograms': WeightUnit.MICROGRAM,
        'μg': WeightUnit.MICROGRAM
    }
    
    def normalize_unit(self, unit_str: str) -> WeightUnit:
        """Normalize unit string to standard WeightUnit enum"""
        normalized = unit_str.lower().strip()
        
        if normalized in self.UNIT_ALIASES:
            return self.UNIT_ALIASES[normalized]
        
        raise ValueError(f"Unsupported weight unit: '{unit_str}'. Supported units: {list(self.UNIT_ALIASES.keys())}")


class WeightConverter:
    """High-precision weight unit converter using Decimal arithmetic"""
    
    # Conversion factors to grams (base unit) with maximum precision
    CONVERSION_FACTORS = {
        WeightUnit.GRAM: Decimal('1'),
        WeightUnit.KILOGRAM: Decimal('1000'),
        WeightUnit.POUND: Decimal('453.59237'),  # Exact international pound
        WeightUnit.OUNCE: Decimal('28.349523125'),  # Exact avoirdupois ounce
        WeightUnit.STONE: Decimal('6350.29318'),  # 14 pounds exactly
        WeightUnit.METRIC_TON: Decimal('1000000'),
        WeightUnit.SHORT_TON: Decimal('907184.74'),  # 2000 pounds exactly
        WeightUnit.MILLIGRAM: Decimal('0.001'),
        WeightUnit.MICROGRAM: Decimal('0.000001')
    }
    
    def convert(self, value: Decimal, from_unit: WeightUnit, to_unit: WeightUnit) -> Decimal:
        """Convert weight between units with maximum precision"""
        if from_unit == to_unit:
            return value
        
        # Convert to grams first (base unit)
        grams = value * self.CONVERSION_FACTORS[from_unit]
        
        # Convert from grams to target unit
        result = grams / self.CONVERSION_FACTORS[to_unit]
        
        # Quantize to internal precision (6 decimal places)
        return result.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    
    def convert_to_kg(self, value: Decimal, from_unit: WeightUnit) -> Decimal:
        """Convert any weight to kilograms (internal standard)"""
        return self.convert(value, from_unit, WeightUnit.KILOGRAM)
    
    def convert_from_kg(self, kg_value: Decimal, to_unit: WeightUnit) -> Decimal:
        """Convert from kilograms to any other unit"""
        return self.convert(kg_value, WeightUnit.KILOGRAM, to_unit)
    
    def get_conversion_factor(self, from_unit: WeightUnit, to_unit: WeightUnit) -> Decimal:
        """Get direct conversion factor between two units"""
        if from_unit == to_unit:
            return Decimal('1')
        
        from_grams = self.CONVERSION_FACTORS[from_unit]
        to_grams = self.CONVERSION_FACTORS[to_unit]
        
        return from_grams / to_grams


class ConversionResult(BaseModel):
    """Result of weight conversion with metadata"""
    original_value: Decimal
    original_unit: WeightUnit
    converted_value: Decimal
    converted_unit: WeightUnit
    conversion_factor: Decimal
    precision_loss: bool = False
    calculation_method: str = "decimal_arithmetic"
    
    model_config = ConfigDict(
        json_encoders={Decimal: float}
    )


class PrecisionManager:
    """Manages numerical precision throughout weight processing"""
    
    INTERNAL_PRECISION = Decimal('0.000001')  # 6 decimal places
    DISPLAY_PRECISION_MAP = {
        WeightUnit.KILOGRAM: 3,
        WeightUnit.POUND: 2, 
        WeightUnit.GRAM: 1,
        WeightUnit.OUNCE: 2,
        WeightUnit.STONE: 3,
        WeightUnit.METRIC_TON: 6,
        WeightUnit.SHORT_TON: 6,
        WeightUnit.MILLIGRAM: 0,
        WeightUnit.MICROGRAM: 0
    }
    
    def quantize_for_display(self, value: Decimal, unit: WeightUnit) -> Decimal:
        """Quantize value for display based on unit-specific precision"""
        precision_places = self.DISPLAY_PRECISION_MAP.get(unit, 3)
        quantizer = Decimal('0.1') ** precision_places
        return value.quantize(quantizer, rounding=ROUND_HALF_UP)
    
    def check_precision_loss(self, original: Decimal, processed: Decimal, threshold: Decimal = Decimal('0.000001')) -> bool:
        """Check if precision loss occurred during conversion"""
        if original == 0:
            return processed != 0
        difference = abs(original - processed)
        relative_error = difference / original
        return relative_error > threshold


class PrecisionReport(BaseModel):
    """Report on precision analysis"""
    has_precision_loss: bool
    precision_errors: List[str] = Field(default_factory=list)
    final_precision: int


class WeightValidator:
    """Validates weight inputs against business rules and constraints"""
    
    def __init__(self, config_service: IConfigurationService):
        self.config = config_service
        self.rules = WeightValidationRules()
        self.unit_validator = UnitValidator()
        self.converter = WeightConverter()
        
        # Load dynamic constraints from CONFIG_SYSTEM_SPEC
        self.min_weight = Decimal(str(config_service.get("validation.min_weight_kg", 0.001)))
        self.max_weight = Decimal(str(config_service.get("validation.max_weight_kg", 1000000)))
    
    def validate_input(self, weight_input: str) -> ValidationResult:
        """Comprehensive input validation with detailed error reporting"""
        errors = []
        warnings = []
        
        # Step 1: Basic format validation
        if not weight_input or not weight_input.strip():
            errors.append(ValidationError(
                code="WEIGHT_001",
                message="Weight input cannot be empty",
                category=ErrorCategory.CLIENT_ERROR,
                field="weight_input"
            ))
            return ValidationResult(is_valid=False, errors=errors)
        
        # Step 2: Length validation
        if len(weight_input) > 100:
            errors.append(ValidationError(
                code="WEIGHT_002",
                message="Weight input exceeds maximum length of 100 characters",
                category=ErrorCategory.CLIENT_ERROR,
                field="weight_input"
            ))
        
        # Step 3: Pattern matching
        parsed_components = self._parse_weight_components(weight_input)
        if not parsed_components:
            errors.append(ValidationError(
                code="WEIGHT_003",
                message=f"Unable to parse weight format: '{weight_input}'. Expected formats: '5 kg', '10.5 lbs', '2.5kg', etc.",
                category=ErrorCategory.BUSINESS_LOGIC_ERROR,
                field="weight_input",
                remediation_hint="Use formats like '5 kg', '10.5 pounds', or '2.5kg'"
            ))
            return ValidationResult(is_valid=False, errors=errors)
        
        # Step 4: Numeric validation
        try:
            numeric_value = Decimal(str(parsed_components['value']))
        except (ValueError, TypeError, InvalidOperation):
            errors.append(ValidationError(
                code="WEIGHT_004",
                message=f"Invalid numeric value: '{parsed_components['value']}'",
                category=ErrorCategory.CLIENT_ERROR,
                field="weight_input"
            ))
            return ValidationResult(is_valid=False, errors=errors)
        
        # Step 5: Positive number validation
        if numeric_value <= 0:
            errors.append(ValidationError(
                code="WEIGHT_005",
                message="Weight must be a positive number greater than zero",
                category=ErrorCategory.CLIENT_ERROR,
                field="weight_input"
            ))
        
        # Step 6: Range validation
        try:
            weight_in_kg = self._convert_to_kg(numeric_value, parsed_components['unit'])
            if weight_in_kg < self.min_weight:
                errors.append(ValidationError(
                    code="WEIGHT_006",
                    message=f"Weight {weight_in_kg} kg is below minimum threshold of {self.min_weight} kg",
                    category=ErrorCategory.CLIENT_ERROR,
                    field="weight_input"
                ))
            
            if weight_in_kg > self.max_weight:
                errors.append(ValidationError(
                    code="WEIGHT_007",
                    message=f"Weight {weight_in_kg} kg exceeds maximum threshold of {self.max_weight} kg",
                    category=ErrorCategory.CLIENT_ERROR,
                    field="weight_input"
                ))
        except ValueError as e:
            errors.append(ValidationError(
                code="WEIGHT_008",
                message=str(e),
                category=ErrorCategory.CLIENT_ERROR,
                field="weight_input"
            ))
        
        # Step 7: Precision validation
        if numeric_value.as_tuple().exponent < -self.rules.MAX_DECIMAL_PLACES:
            warnings.append(ValidationWarning(
                code="WEIGHT_W001",
                message=f"Weight precision exceeds {self.rules.MAX_DECIMAL_PLACES} decimal places, will be rounded",
                field="weight_input"
            ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            parsed_value=numeric_value,
            parsed_unit=parsed_components['unit'] if parsed_components else None
        )
    
    def _parse_weight_components(self, weight_input: str) -> Optional[Dict[str, str]]:
        """Parse weight input into numeric value and unit components"""
        weight_input = weight_input.strip()
        
        # Try standard decimal with unit pattern
        for pattern_name, pattern in self.rules.WEIGHT_PATTERNS.items():
            match = re.match(pattern, weight_input, re.IGNORECASE)
            if match:
                if pattern_name == 'decimal_with_unit':
                    return {'value': match.group(1), 'unit': match.group(2)}
                elif pattern_name == 'scientific':
                    return {'value': match.group(1), 'unit': match.group(2)}
                elif pattern_name == 'range':
                    # For range, take the middle value
                    min_val = float(match.group(1))
                    max_val = float(match.group(2))
                    middle_val = (min_val + max_val) / 2
                    return {'value': str(middle_val), 'unit': match.group(3)}
        
        # Try simple number followed by unit (with flexible spacing, including negative)
        simple_pattern = r'^(-?\d+(?:\.\d+)?)\s*([a-zA-Z]+)$'
        match = re.match(simple_pattern, weight_input, re.IGNORECASE)
        if match:
            return {'value': match.group(1), 'unit': match.group(2)}
        
        return None
    
    def _convert_to_kg(self, value: Decimal, unit_str: str) -> Decimal:
        """Convert value to kg for range validation"""
        try:
            unit = self.unit_validator.normalize_unit(unit_str)
            return self.converter.convert_to_kg(value, unit)
        except ValueError as e:
            raise ValueError(f"Unsupported unit: {unit_str}")


class AIProviderWeightRanges:
    """Weight ranges for AI provider context generation"""
    
    WEIGHT_CATEGORIES = {
        'microscopic': {
            'range': (Decimal('0.000001'), Decimal('0.001')),  # 1μg to 1mg
            'objects': ['virus particles', 'DNA molecules', 'protein molecules'],
            'preferred_unit': WeightUnit.MICROGRAM
        },
        'very_light': {
            'range': (Decimal('0.001'), Decimal('0.1')),  # 1mg to 100mg
            'objects': ['insects', 'small pills', 'paper clips'],
            'preferred_unit': WeightUnit.GRAM
        },
        'light': {
            'range': (Decimal('0.1'), Decimal('10')),  # 100mg to 10kg
            'objects': ['smartphones', 'books', 'laptops', 'cats'],
            'preferred_unit': WeightUnit.KILOGRAM
        },
        'medium': {
            'range': (Decimal('10'), Decimal('1000')),  # 10kg to 1000kg
            'objects': ['people', 'furniture', 'motorcycles', 'pianos'],
            'preferred_unit': WeightUnit.KILOGRAM
        },
        'heavy': {
            'range': (Decimal('1000'), Decimal('100000')),  # 1 ton to 100 tons
            'objects': ['cars', 'elephants', 'trucks', 'small buildings'],
            'preferred_unit': WeightUnit.METRIC_TON
        },
        'very_heavy': {
            'range': (Decimal('100000'), Decimal('1000000')),  # 100 tons to 1000 tons
            'objects': ['trains', 'commercial aircraft', 'large buildings'],
            'preferred_unit': WeightUnit.METRIC_TON
        }
    }
    
    def get_weight_category(self, weight_kg: Decimal) -> str:
        """Determine weight category for AI context"""
        for category, info in self.WEIGHT_CATEGORIES.items():
            min_weight, max_weight = info['range']
            if min_weight <= weight_kg < max_weight:
                return category
        return 'extreme'
    
    def get_comparable_objects(self, weight_kg: Decimal) -> List[str]:
        """Get list of comparable objects for AI provider"""
        category = self.get_weight_category(weight_kg)
        if category in self.WEIGHT_CATEGORIES:
            return self.WEIGHT_CATEGORIES[category]['objects']
        return ['astronomical objects', 'geological formations']
    
    def get_preferred_unit(self, weight_kg: Decimal) -> WeightUnit:
        """Get preferred unit for the weight category"""
        category = self.get_weight_category(weight_kg)
        if category in self.WEIGHT_CATEGORIES:
            return self.WEIGHT_CATEGORIES[category]['preferred_unit']
        return WeightUnit.KILOGRAM


class WeightFormatter:
    """Formats weights for display with locale support"""
    
    LOCALE_PREFERENCES = {
        'US': {'primary_unit': WeightUnit.POUND, 'decimal_separator': '.', 'thousands_separator': ','},
        'UK': {'primary_unit': WeightUnit.STONE, 'decimal_separator': '.', 'thousands_separator': ','},
        'EU': {'primary_unit': WeightUnit.KILOGRAM, 'decimal_separator': ',', 'thousands_separator': '.'},
        'default': {'primary_unit': WeightUnit.KILOGRAM, 'decimal_separator': '.', 'thousands_separator': ','}
    }
    
    def __init__(self, config_service: IConfigurationService):
        self.config = config_service
        self.converter = WeightConverter()
        self.precision_manager = PrecisionManager()
    
    def format_for_locale(self, weight_kg: Decimal, locale: str = 'default') -> str:
        """Format weight according to locale preferences"""
        preferences = self.LOCALE_PREFERENCES.get(locale, self.LOCALE_PREFERENCES['default'])
        
        # Convert to preferred unit
        preferred_unit = preferences['primary_unit']
        converted_value = self.converter.convert_from_kg(weight_kg, preferred_unit)
        
        # Apply locale-specific formatting
        formatted = self._apply_locale_formatting(converted_value, preferences)
        
        return f"{formatted} {preferred_unit.value}"
    
    def _apply_locale_formatting(self, value: Decimal, preferences: Dict[str, Any]) -> str:
        """Apply locale-specific number formatting"""
        # For simplicity, using standard formatting with thousands separators
        return f"{value:,}"
    
    def _format_with_separators(self, value: Decimal, unit: WeightUnit) -> str:
        """Format weight with thousands separators and unit label"""
        # Convert to string and add thousands separators
        value_str = f"{value:,}"
        
        # Add appropriate unit label
        unit_labels = {
            WeightUnit.KILOGRAM: 'kg',
            WeightUnit.GRAM: 'g', 
            WeightUnit.POUND: 'lbs',
            WeightUnit.METRIC_TON: 'metric tons'
        }
        
        unit_label = unit_labels.get(unit, unit.value)
        return f"{value_str} {unit_label}"


class NormalizedWeight(BaseModel):
    """Normalized weight representation for internal processing"""
    original_input: str
    weight_kg: Decimal = Field(..., decimal_places=6)
    parsed_value: Decimal
    parsed_unit: WeightUnit
    display_value: Decimal
    display_unit: WeightUnit
    display_string: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    
    model_config = ConfigDict(
        json_encoders={Decimal: float}
    )


class WeightNormalizer:
    """Normalizes weight data for internal processing and external display"""
    
    def __init__(self, config_service: IConfigurationService):
        self.config = config_service
        self.converter = WeightConverter()
        self.precision_manager = PrecisionManager()
        self.validator = WeightValidator(config_service)
    
    def normalize_weight_input(self, weight_input: str) -> NormalizedWeight:
        """Complete normalization pipeline for weight input"""
        # Step 1: Parse and validate input
        validation_result = self.validator.validate_input(weight_input)
        if not validation_result.is_valid:
            raise WeightValidationException(validation_result.errors)
        
        # Step 2: Convert to internal standard (kg)
        unit_validator = UnitValidator()
        weight_unit = unit_validator.normalize_unit(validation_result.parsed_unit)
        weight_kg = self.converter.convert_to_kg(validation_result.parsed_value, weight_unit)
        
        # Step 3: Apply internal precision
        normalized_kg = weight_kg.quantize(self.precision_manager.INTERNAL_PRECISION)
        
        # Step 4: Determine optimal display unit and format
        display_info = self._determine_display_format(normalized_kg)
        
        return NormalizedWeight(
            original_input=weight_input,
            weight_kg=normalized_kg,
            parsed_value=validation_result.parsed_value,
            parsed_unit=weight_unit,
            display_value=display_info['value'],
            display_unit=display_info['unit'],
            display_string=display_info['formatted'],
            confidence=validation_result.confidence
        )
    
    def _determine_display_format(self, weight_kg: Decimal) -> Dict[str, Any]:
        """Determine optimal display format based on weight magnitude"""
        # Use original unit if within reasonable display range
        if Decimal('0.001') <= weight_kg <= Decimal('1000'):
            display_unit = WeightUnit.KILOGRAM
            display_value = weight_kg
        elif weight_kg < Decimal('0.001'):
            display_unit = WeightUnit.GRAM
            display_value = self.converter.convert_from_kg(weight_kg, WeightUnit.GRAM)
        else:
            display_unit = WeightUnit.METRIC_TON
            display_value = self.converter.convert_from_kg(weight_kg, WeightUnit.METRIC_TON)
        
        # Apply unit-specific precision
        formatted_value = self.precision_manager.quantize_for_display(display_value, display_unit)
        
        # Format for display with thousands separators
        formatted_string = self._format_with_separators(formatted_value, display_unit)
        
        return {
            'value': formatted_value,
            'unit': display_unit,
            'formatted': formatted_string
        }
    
    def _format_with_separators(self, value: Decimal, unit: WeightUnit) -> str:
        """Format weight with thousands separators and unit label"""
        # Convert to string and add thousands separators
        value_str = f"{value:,}"
        
        # Add appropriate unit label
        unit_labels = {
            WeightUnit.KILOGRAM: 'kg',
            WeightUnit.GRAM: 'g', 
            WeightUnit.POUND: 'lbs',
            WeightUnit.METRIC_TON: 'metric tons'
        }
        
        unit_label = unit_labels.get(unit, unit.value)
        return f"{value_str} {unit_label}"


class EdgeCaseResult(BaseModel):
    """Result of edge case handling"""
    adjusted_weight: Decimal
    warnings: List[str] = Field(default_factory=list)
    adjustments: List[str] = Field(default_factory=list)
    is_extreme: bool = False


class EdgeCaseHandler:
    """Handles edge cases in weight processing"""
    
    def handle_extreme_weights(self, weight_kg: Decimal) -> EdgeCaseResult:
        """Handle extremely small or large weight values"""
        warnings = []
        adjustments = []
        
        # Handle extremely small weights
        if weight_kg < Decimal('0.000001'):  # Less than 1 microgram
            warnings.append("Weight is extremely small and may have limited comparison value")
            if weight_kg < Decimal('1e-15'):  # Approaching atomic scale
                adjustments.append("Weight adjusted to minimum representable value")
                weight_kg = Decimal('1e-15')
        
        # Handle extremely large weights
        if weight_kg > Decimal('1e15'):  # Larger than Earth's mass
            warnings.append("Weight exceeds astronomical scales")
            if weight_kg > Decimal('1e20'):
                adjustments.append("Weight capped at maximum representable value")
                weight_kg = Decimal('1e20')
        
        return EdgeCaseResult(
            adjusted_weight=weight_kg,
            warnings=warnings,
            adjustments=adjustments,
            is_extreme=len(warnings) > 0
        )
    
    def handle_precision_limits(self, value: Decimal) -> Decimal:
        """Handle precision limits and rounding"""
        # Check if value exceeds our precision capabilities
        if value.as_tuple().exponent < -6:
            # Round to 6 decimal places
            return value.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
        
        return value


class WeightProcessingException(Exception):
    """Base exception for weight processing errors"""
    def __init__(self, message: str, category: ErrorCategory = ErrorCategory.BUSINESS_LOGIC_ERROR):
        super().__init__(message)
        self.category = category


class WeightValidationException(WeightProcessingException):
    """Exception for weight validation failures"""
    def __init__(self, validation_errors: List[ValidationError]):
        self.errors = validation_errors
        super().__init__(f"Weight validation failed with {len(validation_errors)} errors", ErrorCategory.CLIENT_ERROR)


class WeightConversionException(WeightProcessingException):
    """Exception for unit conversion failures"""
    def __init__(self, message: str):
        super().__init__(message, ErrorCategory.BUSINESS_LOGIC_ERROR)


class WeightItem(BaseModel):
    """Weight item model for API responses - EXACT match with BACKEND_CORE_SPEC"""
    name: str = Field(default="processed_weight", min_length=1, max_length=100)
    original_input: str = Field(..., min_length=1)
    weight_kg: Decimal = Field(..., gt=Decimal('0.0001'), le=Decimal('1000000'))
    weight_display: str = Field(..., min_length=1)
    unit_used: WeightUnit
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    
    @field_validator('weight_kg')
    @classmethod
    def validate_precision(cls, v):
        """Ensure internal precision compliance"""
        return v.quantize(Decimal('0.000001'))


class WeightRange(BaseModel):
    """Weight ranges for AI provider context"""
    min_weight_kg: Decimal = Field(..., gt=Decimal('0'))
    max_weight_kg: Decimal = Field(..., gt=Decimal('0'))
    typical_objects: List[str] = Field(..., min_length=1)
    unit_preference: WeightUnit = Field(default=WeightUnit.KILOGRAM)


class ProcessingMetadata(BaseModel):
    """Metadata about weight processing operation"""
    processing_time_ms: int = Field(..., ge=0)
    conversion_method: str
    precision_applied: int
    edge_cases_detected: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class WeightProcessor:
    """Central weight processing engine with Decimal precision"""
    
    def __init__(self, config_service: Optional[IConfigurationService] = None):
        self.config = config_service or SimpleConfig()
        self.validator = WeightValidator(self.config)
        self.converter = WeightConverter()
        self.formatter = WeightFormatter(self.config)
        self.normalizer = WeightNormalizer(self.config)
        self.edge_case_handler = EdgeCaseHandler()
        self.ai_weight_ranges = AIProviderWeightRanges()
        self.precision_manager = PrecisionManager()
        
        # Precision settings from CONFIG_SYSTEM_SPEC
        self.internal_precision = Decimal('0.000001')  # 6 decimal places
        self.display_precision = self.config.get("comparison.precision", 2)
        
        logger.info("WeightProcessor initialized with high-precision Decimal arithmetic")
    
    def process_weight(self, weight_input: str, target_unit: Optional[WeightUnit] = None) -> WeightItem:
        """
        Main processing method that handles weight input through complete pipeline
        
        Args:
            weight_input: Raw weight string input
            target_unit: Optional target unit for conversion
            
        Returns:
            WeightItem: Processed weight with all metadata
            
        Raises:
            WeightValidationException: If validation fails
            WeightConversionException: If conversion fails
        """
        start_time = time.time()
        
        try:
            # Step 1: Normalize weight input
            normalized_weight = self.normalizer.normalize_weight_input(weight_input)
            
            # Step 2: Handle edge cases
            edge_result = self.edge_case_handler.handle_extreme_weights(normalized_weight.weight_kg)
            if edge_result.is_extreme:
                normalized_weight.weight_kg = edge_result.adjusted_weight
                logger.warning(f"Edge case handling applied: {edge_result.warnings}")
            
            # Step 3: Convert to target unit if specified
            if target_unit:
                display_value = self.converter.convert_from_kg(normalized_weight.weight_kg, target_unit)
                display_string = self.formatter._format_with_separators(display_value, target_unit)
                unit_used = target_unit
            else:
                display_value = normalized_weight.display_value
                display_string = normalized_weight.display_string
                unit_used = normalized_weight.parsed_unit
            
            # Step 4: Create WeightItem
            weight_item = WeightItem(
                original_input=weight_input,
                weight_kg=normalized_weight.weight_kg,
                weight_display=display_string,
                unit_used=unit_used,
                confidence=normalized_weight.confidence
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            logger.info(f"Weight processed successfully in {processing_time}ms: {weight_input} -> {normalized_weight.weight_kg} kg")
            
            return weight_item
            
        except WeightValidationException:
            logger.warning(f"Weight validation failed for input: {weight_input}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error processing weight: {weight_input} - {str(e)}")
            raise WeightProcessingException(f"Internal processing error: {str(e)}")
    
    def validate_weight_input(self, weight_input: str) -> ValidationResult:
        """Validate weight input without full processing"""
        return self.validator.validate_input(weight_input)
    
    def convert_weight(self, value: Decimal, from_unit: WeightUnit, to_unit: WeightUnit) -> ConversionResult:
        """Convert weight between units with comprehensive result metadata"""
        original_value = value
        converted_value = self.converter.convert(value, from_unit, to_unit)
        conversion_factor = self.converter.get_conversion_factor(from_unit, to_unit)
        
        # Check for precision loss
        if from_unit != to_unit:
            # Convert back to check precision
            back_converted = self.converter.convert(converted_value, to_unit, from_unit)
            precision_loss = self.precision_manager.check_precision_loss(original_value, back_converted)
        else:
            precision_loss = False
        
        return ConversionResult(
            original_value=original_value,
            original_unit=from_unit,
            converted_value=converted_value,
            converted_unit=to_unit,
            conversion_factor=conversion_factor,
            precision_loss=precision_loss
        )
    
    def get_weight_category(self, weight_kg: Decimal) -> str:
        """Get weight category for AI context generation"""
        return self.ai_weight_ranges.get_weight_category(weight_kg)
    
    def get_comparable_objects(self, weight_kg: Decimal) -> List[str]:
        """Get comparable objects for AI comparison generation"""
        return self.ai_weight_ranges.get_comparable_objects(weight_kg)
    
    def get_weight_range_for_category(self, category: str) -> Optional[WeightRange]:
        """Get weight range information for a specific category"""
        if category in self.ai_weight_ranges.WEIGHT_CATEGORIES:
            cat_info = self.ai_weight_ranges.WEIGHT_CATEGORIES[category]
            min_weight, max_weight = cat_info['range']
            return WeightRange(
                min_weight_kg=min_weight,
                max_weight_kg=max_weight,
                typical_objects=cat_info['objects'],
                unit_preference=cat_info['preferred_unit']
            )
        return None
    
    def format_weight_for_locale(self, weight_kg: Decimal, locale: str = 'default') -> str:
        """Format weight for specific locale"""
        return self.formatter.format_for_locale(weight_kg, locale)
    
    def get_supported_units(self) -> List[str]:
        """Get list of all supported weight units"""
        return list(UnitValidator.UNIT_ALIASES.keys())
    
    def get_processing_metrics(self) -> Dict[str, Any]:
        """Get processing performance and configuration metrics"""
        return {
            "internal_precision_places": 6,
            "display_precision": self.display_precision,
            "supported_units_count": len(self.get_supported_units()),
            "weight_categories_count": len(self.ai_weight_ranges.WEIGHT_CATEGORIES),
            "min_weight_kg": float(self.validator.min_weight),
            "max_weight_kg": float(self.validator.max_weight)
        }


# Error code mapping for comprehensive error tracking
WEIGHT_ERROR_CODES = {
    "WEIGHT_001": "Empty weight input",
    "WEIGHT_002": "Input length exceeded",
    "WEIGHT_003": "Unparseable weight format",
    "WEIGHT_004": "Invalid numeric value",
    "WEIGHT_005": "Non-positive weight",
    "WEIGHT_006": "Weight below minimum threshold",
    "WEIGHT_007": "Weight above maximum threshold",
    "WEIGHT_008": "Unsupported unit",
    "WEIGHT_009": "Precision loss detected",
    "WEIGHT_010": "Conversion failure"
}


def create_weight_processor(config_service: Optional[IConfigurationService] = None) -> WeightProcessor:
    """Factory function to create a WeightProcessor instance"""
    return WeightProcessor(config_service)