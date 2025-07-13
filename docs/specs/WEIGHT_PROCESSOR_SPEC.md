# Weight Processing Engine Specification for SizeComparator

## Document Overview

This specification defines the comprehensive weight processing logic for SizeComparator's backend core system, focusing on precision, validation, unit conversion, and seamless integration with all system components. The weight processor serves as the critical foundation for accurate weight comparisons and must handle edge cases gracefully while maintaining numerical precision throughout all operations.

**Document Length**: 5-6 pages  
**Integration Reference**: BACKEND_CORE_SPEC.md  
**Dependencies**: AI_PROVIDER_SPEC.md, CONFIG_SYSTEM_SPEC.md, ERROR_MONITORING_SPEC.md

## 1. Weight Processing Architecture (1 page)

### 1.1 Core Components

The weight processing engine consists of four primary components that work together to ensure accurate and reliable weight handling:

```python
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Optional, Union, Dict, Any, List
from pydantic import BaseModel, Field, validator
import re

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

class WeightProcessor:
    """Central weight processing engine with Decimal precision"""
    
    def __init__(self, config_service: IConfigurationService):
        self.config = config_service
        self.validator = WeightValidator(config_service)
        self.converter = WeightConverter()
        self.formatter = WeightFormatter(config_service)
        
        # Precision settings from CONFIG_SYSTEM_SPEC
        self.internal_precision = Decimal('0.000001')  # 6 decimal places
        self.display_precision = config_service.get("comparison.precision", 2)
```

### 1.2 Processing Pipeline

The weight processing follows a strict pipeline that ensures data integrity and proper error handling:

1. **Input Parsing**: Parse natural language and numeric weight inputs
2. **Validation**: Validate against range limits and format requirements
3. **Normalization**: Convert to internal Decimal representation in kilograms
4. **Conversion**: Convert between units using high-precision arithmetic
5. **Formatting**: Format for display with appropriate precision and localization

### 1.3 Integration Points

```python
# BACKEND_CORE_SPEC Integration
class WeightItem(BaseModel):
    """Weight item model for API responses - EXACT match with BACKEND_CORE_SPEC"""
    name: str = Field(..., min_length=1, max_length=100)
    original_input: str = Field(..., min_length=1)
    weight_kg: Decimal = Field(..., gt=Decimal('0.001'), le=Decimal('1000000'))
    weight_display: str = Field(..., min_length=1)
    unit_used: WeightUnit
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    
    @validator('weight_kg')
    def validate_precision(cls, v):
        """Ensure internal precision compliance"""
        return v.quantize(Decimal('0.000001'))

# AI_PROVIDER_SPEC Integration
class WeightRange(BaseModel):
    """Weight ranges for AI provider context"""
    min_weight_kg: Decimal = Field(..., gt=Decimal('0'))
    max_weight_kg: Decimal = Field(..., gt=Decimal('0'))
    typical_objects: List[str] = Field(..., min_items=1)
    unit_preference: WeightUnit = Field(default=WeightUnit.KILOGRAM)
```

## 2. Input Validation Framework (1.5 pages)

### 2.1 Validation Rules and Constraints

The weight processor implements comprehensive validation aligned with BACKEND_CORE_SPEC requirements:

```python
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
        'decimal_with_unit': r'^(\d+(?:\.\d+)?)\s*([a-zA-Z]+)$',
        'fraction_with_unit': r'^(\d+/\d+)\s*([a-zA-Z]+)$',
        'mixed_units': r'^(\d+)\s*([a-zA-Z]+)\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]+)$',
        'scientific': r'^(\d+(?:\.\d+)?)[eE][+-]?\d+\s*([a-zA-Z]+)$',
        'range': r'^(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)\s*([a-zA-Z]+)$'
    }

class WeightValidator:
    """Validates weight inputs against business rules and constraints"""
    
    def __init__(self, config_service: IConfigurationService):
        self.config = config_service
        self.rules = WeightValidationRules()
        
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
        except (ValueError, TypeError, InvalidOperation) as e:
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
            parsed_unit=parsed_components['unit']
        )

class ValidationResult(BaseModel):
    """Validation result with comprehensive error reporting"""
    is_valid: bool
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[ValidationWarning] = Field(default_factory=list)
    parsed_value: Optional[Decimal] = None
    parsed_unit: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

class ValidationError(BaseModel):
    """Validation error aligned with ERROR_MONITORING_SPEC"""
    code: str = Field(..., pattern=r'^WEIGHT_\d{3}$')
    message: str = Field(..., min_length=1)
    category: ErrorCategory
    field: str
    remediation_hint: Optional[str] = None
```

### 2.2 Supported Unit Validation

The processor validates units against a comprehensive list of supported weight units:

```python
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
        'short ton': WeightUnit.SHORT_TON, 'short tons': WeightUnit.SHORT_TON
    }
    
    def normalize_unit(self, unit_str: str) -> WeightUnit:
        """Normalize unit string to standard WeightUnit enum"""
        normalized = unit_str.lower().strip()
        
        if normalized in self.UNIT_ALIASES:
            return self.UNIT_ALIASES[normalized]
        
        raise ValueError(f"Unsupported weight unit: '{unit_str}'. Supported units: {list(self.UNIT_ALIASES.keys())}")
```

## 3. High-Precision Unit Conversion (1.5 pages)

### 3.1 Decimal-Based Conversion Engine

All weight conversions use Python's Decimal class to eliminate floating-point precision errors:

```python
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
    
    def __init__(self):
        # Set decimal precision context for all calculations
        getcontext().prec = 28  # High precision for intermediate calculations
        getcontext().rounding = ROUND_HALF_UP
    
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
```

### 3.2 Precision Management

The system maintains strict precision control throughout all calculations:

```python
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
        difference = abs(original - processed)
        relative_error = difference / original if original != 0 else difference
        return relative_error > threshold
    
    def validate_calculation_precision(self, calculation_steps: List[Decimal]) -> PrecisionReport:
        """Validate precision throughout calculation chain"""
        errors = []
        for i, step in enumerate(calculation_steps[1:], 1):
            if self.check_precision_loss(calculation_steps[i-1], step):
                errors.append(f"Precision loss detected at step {i}")
        
        return PrecisionReport(
            has_precision_loss=len(errors) > 0,
            precision_errors=errors,
            final_precision=len(str(calculation_steps[-1]).split('.')[-1]) if '.' in str(calculation_steps[-1]) else 0
        )
```

### 3.3 AI Provider Weight Range Integration

The weight processor integrates with AI_PROVIDER_SPEC to provide appropriate weight ranges for comparison generation:

```python
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
```

## 4. Weight Normalization and Formatting (1 page)

### 4.1 Normalization Pipeline

Weight normalization ensures consistent internal representation while preserving display preferences:

```python
class WeightNormalizer:
    """Normalizes weight data for internal processing and external display"""
    
    def __init__(self, config_service: IConfigurationService):
        self.config = config_service
        self.converter = WeightConverter()
        self.precision_manager = PrecisionManager()
    
    def normalize_weight_input(self, weight_input: str) -> NormalizedWeight:
        """Complete normalization pipeline for weight input"""
        # Step 1: Parse and validate input
        validation_result = WeightValidator(self.config).validate_input(weight_input)
        if not validation_result.is_valid:
            raise WeightValidationException(validation_result.errors)
        
        # Step 2: Convert to internal standard (kg)
        weight_kg = self.converter.convert_to_kg(
            validation_result.parsed_value, 
            WeightUnit(validation_result.parsed_unit)
        )
        
        # Step 3: Apply internal precision
        normalized_kg = weight_kg.quantize(self.precision_manager.INTERNAL_PRECISION)
        
        # Step 4: Determine optimal display unit and format
        display_info = self._determine_display_format(normalized_kg)
        
        return NormalizedWeight(
            original_input=weight_input,
            weight_kg=normalized_kg,
            parsed_value=validation_result.parsed_value,
            parsed_unit=WeightUnit(validation_result.parsed_unit),
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
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }
```

### 4.2 Internationalization Support

The formatter supports multiple locales and unit preferences:

```python
class WeightFormatter:
    """Formats weights for display with locale support"""
    
    LOCALE_PREFERENCES = {
        'US': {'primary_unit': WeightUnit.POUND, 'decimal_separator': '.', 'thousands_separator': ','},
        'UK': {'primary_unit': WeightUnit.STONE, 'decimal_separator': '.', 'thousands_separator': ','},
        'EU': {'primary_unit': WeightUnit.KILOGRAM, 'decimal_separator': ',', 'thousands_separator': '.'},
        'default': {'primary_unit': WeightUnit.KILOGRAM, 'decimal_separator': '.', 'thousands_separator': ','}
    }
    
    def format_for_locale(self, weight_kg: Decimal, locale: str = 'default') -> str:
        """Format weight according to locale preferences"""
        preferences = self.LOCALE_PREFERENCES.get(locale, self.LOCALE_PREFERENCES['default'])
        
        # Convert to preferred unit
        preferred_unit = preferences['primary_unit']
        converted_value = self.converter.convert_from_kg(weight_kg, preferred_unit)
        
        # Apply locale-specific formatting
        formatted = self._apply_locale_formatting(converted_value, preferences)
        
        return f"{formatted} {preferred_unit.value}"
```

## 5. Edge Case Handling (1 page)

### 5.1 Extreme Weight Values

The processor handles edge cases for very small and very large weights:

```python
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
    
    def handle_mixed_units(self, input_text: str) -> MixedUnitResult:
        """Handle inputs with mixed units (e.g., '5 lbs 3 oz')"""
        patterns = {
            'pounds_ounces': r'(\d+(?:\.\d+)?)\s*(?:lbs?|pounds?)\s*(\d+(?:\.\d+)?)\s*(?:oz|ounces?)',
            'stones_pounds': r'(\d+(?:\.\d+)?)\s*(?:st|stones?)\s*(\d+(?:\.\d+)?)\s*(?:lbs?|pounds?)',
            'kg_grams': r'(\d+(?:\.\d+)?)\s*kg\s*(\d+(?:\.\d+)?)\s*(?:g|grams?)'
        }
        
        for pattern_name, pattern in patterns.items():
            match = re.search(pattern, input_text, re.IGNORECASE)
            if match:
                return self._process_mixed_unit_match(pattern_name, match)
        
        raise WeightParsingException(f"Unable to parse mixed unit format: {input_text}")

class EdgeCaseResult(BaseModel):
    """Result of edge case handling"""
    adjusted_weight: Decimal
    warnings: List[str] = Field(default_factory=list)
    adjustments: List[str] = Field(default_factory=list)
    is_extreme: bool = False
```

### 5.2 Error Recovery Strategies

```python
class WeightErrorRecovery:
    """Provides error recovery and fallback strategies"""
    
    def attempt_fuzzy_parsing(self, failed_input: str) -> Optional[NormalizedWeight]:
        """Attempt to parse weight using fuzzy matching"""
        # Remove common typos and extra characters
        cleaned = re.sub(r'[^\d\.\s\w]', '', failed_input)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        # Try common corrections
        corrections = {
            'kilos': 'kg',
            'pounds': 'lbs', 
            'grams': 'g',
            'kilo': 'kg'
        }
        
        for typo, correction in corrections.items():
            if typo in cleaned.lower():
                corrected = cleaned.lower().replace(typo, correction)
                try:
                    return WeightNormalizer(self.config).normalize_weight_input(corrected)
                except WeightValidationException:
                    continue
        
        return None
    
    def suggest_corrections(self, failed_input: str) -> List[str]:
        """Suggest corrections for failed weight parsing"""
        suggestions = []
        
        # Extract numbers from input
        numbers = re.findall(r'\d+(?:\.\d+)?', failed_input)
        if numbers:
            number = numbers[0]
            suggestions.extend([
                f"{number} kg",
                f"{number} lbs", 
                f"{number} grams"
            ])
        
        return suggestions
```

## 6. API Interfaces and Error Handling (1 page)

### 6.1 Exact API Interfaces

The weight processor provides exact interfaces for API_ENDPOINTS_SPEC and DATA_MODELS_SPEC integration:

```python
# API Endpoint Integration
class WeightProcessingRequest(BaseModel):
    """Request model for weight processing endpoints"""
    weight_input: str = Field(..., min_length=1, max_length=100, description="Weight with optional unit")
    target_unit: Optional[WeightUnit] = Field(None, description="Desired output unit")
    locale: Optional[str] = Field('default', description="Locale for formatting")
    validation_level: Optional[str] = Field('standard', description="Validation strictness")

class WeightProcessingResponse(BaseModel):
    """Response model aligned with BACKEND_CORE_SPEC"""
    weight_item: WeightItem
    processing_metadata: ProcessingMetadata
    validation_results: Optional[ValidationResult] = None

class ProcessingMetadata(BaseModel):
    """Metadata about weight processing operation"""
    processing_time_ms: int = Field(..., ge=0)
    conversion_method: str
    precision_applied: int
    edge_cases_detected: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

# FastAPI Endpoint Implementation
@router.post("/api/v1/weights/process", response_model=WeightProcessingResponse)
async def process_weight(
    request: WeightProcessingRequest,
    weight_processor: WeightProcessor = Depends(get_weight_processor),
    request_id: str = Depends(get_request_id)
) -> WeightProcessingResponse:
    """Process weight input with comprehensive validation and normalization"""
    start_time = time.time()
    
    try:
        # Process weight input
        normalized_weight = weight_processor.normalize_weight_input(request.weight_input)
        
        # Convert to target unit if specified
        if request.target_unit:
            display_value = weight_processor.converter.convert_from_kg(
                normalized_weight.weight_kg, 
                request.target_unit
            )
            display_string = weight_processor.formatter.format_for_locale(
                display_value, 
                request.locale
            )
        else:
            display_value = normalized_weight.display_value
            display_string = normalized_weight.display_string
        
        # Create WeightItem response
        weight_item = WeightItem(
            name="",  # Will be populated by calling service
            original_input=request.weight_input,
            weight_kg=normalized_weight.weight_kg,
            weight_display=display_string,
            unit_used=normalized_weight.parsed_unit,
            confidence=normalized_weight.confidence
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return WeightProcessingResponse(
            weight_item=weight_item,
            processing_metadata=ProcessingMetadata(
                processing_time_ms=processing_time,
                conversion_method="decimal_arithmetic",
                precision_applied=6,
                edge_cases_detected=[],
                warnings=[]
            )
        )
        
    except WeightValidationException as e:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error_code="WEIGHT_VALIDATION_FAILED",
                error_category=ErrorCategory.CLIENT_ERROR,
                message=str(e),
                request_id=request_id,
                severity=ErrorSeverity.INFO,
                details={"validation_errors": [error.dict() for error in e.errors]}
            ).dict()
        )
```

### 6.2 Error Response Specifications

All weight processing errors align with ERROR_MONITORING_SPEC categories:

```python
class WeightProcessingException(Exception):
    """Base exception for weight processing errors"""
    category: ErrorCategory = ErrorCategory.BUSINESS_LOGIC_ERROR
    severity: ErrorSeverity = ErrorSeverity.WARNING

class WeightValidationException(WeightProcessingException):
    """Exception for weight validation failures"""
    category = ErrorCategory.CLIENT_ERROR
    severity = ErrorSeverity.INFO
    
    def __init__(self, validation_errors: List[ValidationError]):
        self.errors = validation_errors
        super().__init__(f"Weight validation failed with {len(validation_errors)} errors")

class WeightConversionException(WeightProcessingException):
    """Exception for unit conversion failures"""
    category = ErrorCategory.BUSINESS_LOGIC_ERROR
    severity = ErrorSeverity.WARNING

class WeightRangeException(WeightProcessingException):
    """Exception for out-of-range weight values"""
    category = ErrorCategory.CLIENT_ERROR
    severity = ErrorSeverity.INFO

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
```

This specification provides comprehensive coverage of weight processing logic while ensuring seamless integration with all SizeComparator system components. The design emphasizes precision, reliability, and proper error handling aligned with the established architectural patterns.