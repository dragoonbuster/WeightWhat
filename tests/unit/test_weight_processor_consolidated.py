"""
Consolidated unit tests for WeightProcessor component.

This module consolidates all weight processing tests including validation,
conversion, normalization, edge cases, and error handling.
"""

import pytest
from decimal import Decimal
from typing import Any

from src.services.weight_processor import (
    WeightProcessor,
    WeightUnit,
    WeightValidator,
    WeightConverter,
    WeightNormalizer,
    UnitValidator,
    AIProviderWeightRanges,
    WeightFormatter,
    EdgeCaseHandler,
    PrecisionManager,
    WeightValidationException,
    WeightConversionException,
    ValidationResult,
    ValidationError,
    ConversionResult,
    NormalizedWeight,
    WeightItem,
    SimpleConfig,
    WEIGHT_ERROR_CODES
)


class TestWeightProcessor:
    """Test the main WeightProcessor class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = SimpleConfig()
        self.processor = WeightProcessor(self.config)
    
    def test_initialization(self):
        """Test processor initialization"""
        assert self.processor.config is not None
        assert self.processor.validator is not None
        assert self.processor.converter is not None
        assert self.processor.formatter is not None
        assert self.processor.normalizer is not None
        assert self.processor.internal_precision == Decimal('0.000001')
    
    def test_process_weight_basic(self):
        """Test basic weight processing"""
        result = self.processor.process_weight("5 kg")
        
        assert isinstance(result, WeightItem)
        assert result.original_input == "5 kg"
        assert result.weight_kg == Decimal('5.000000')
        assert result.unit_used == WeightUnit.KILOGRAM
        assert result.confidence == 1.0
    
    def test_process_weight_with_conversion(self):
        """Test weight processing with unit conversion"""
        result = self.processor.process_weight("10 lbs", target_unit=WeightUnit.KILOGRAM)
        
        assert isinstance(result, WeightItem)
        assert result.original_input == "10 lbs"
        assert abs(result.weight_kg - Decimal('4.535924')) < Decimal('0.000001')
        assert result.unit_used == WeightUnit.KILOGRAM
    
    def test_process_weight_validation_error(self):
        """Test processing with validation errors"""
        with pytest.raises(WeightValidationException) as exc_info:
            self.processor.process_weight("")
        
        assert len(exc_info.value.errors) > 0
        assert exc_info.value.errors[0].code == "WEIGHT_001"
    
    def test_validate_weight_input(self):
        """Test weight input validation"""
        result = self.processor.validate_weight_input("5.5 kg")
        
        assert result.is_valid is True
        assert result.parsed_value == Decimal('5.5')
        assert result.parsed_unit == "kg"
        assert len(result.errors) == 0
    
    def test_convert_weight(self):
        """Test weight conversion"""
        result = self.processor.convert_weight(
            Decimal('1'), WeightUnit.KILOGRAM, WeightUnit.POUND
        )
        
        assert isinstance(result, ConversionResult)
        assert result.original_value == Decimal('1')
        assert result.original_unit == WeightUnit.KILOGRAM
        assert result.converted_unit == WeightUnit.POUND
        assert abs(result.converted_value - Decimal('2.204623')) < Decimal('0.000001')
    
    def test_get_weight_category(self):
        """Test weight categorization"""
        assert self.processor.get_weight_category(Decimal('0.5')) == 'light'
        assert self.processor.get_weight_category(Decimal('50')) == 'medium'
        assert self.processor.get_weight_category(Decimal('5000')) == 'heavy'
    
    def test_get_comparable_objects(self):
        """Test getting comparable objects"""
        objects = self.processor.get_comparable_objects(Decimal('0.5'))
        assert isinstance(objects, list)
        assert len(objects) > 0
        assert any(obj in ['smartphones', 'books', 'laptops', 'cats'] for obj in objects)
    
    def test_get_supported_units(self):
        """Test getting supported units"""
        units = self.processor.get_supported_units()
        assert isinstance(units, list)
        assert 'kg' in units
        assert 'lbs' in units or 'lb' in units
        assert 'g' in units
    
    def test_get_processing_metrics(self):
        """Test getting processing metrics"""
        metrics = self.processor.get_processing_metrics()
        assert isinstance(metrics, dict)
        assert 'internal_precision_places' in metrics
        assert 'supported_units_count' in metrics
        assert metrics['internal_precision_places'] == 6


class TestWeightValidator:
    """Test weight validation functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = SimpleConfig()
        self.validator = WeightValidator(self.config)
    
    def test_validate_valid_input(self):
        """Test validation of valid weight input"""
        result = self.validator.validate_input("5.5 kg")
        
        assert result.is_valid is True
        assert result.parsed_value == Decimal('5.5')
        assert result.parsed_unit == "kg"
        assert len(result.errors) == 0
    
    def test_validate_empty_input(self):
        """Test validation of empty input"""
        result = self.validator.validate_input("")
        
        assert result.is_valid is False
        assert len(result.errors) == 1
        assert result.errors[0].code == "WEIGHT_001"
    
    def test_validate_invalid_format(self):
        """Test validation of invalid format"""
        result = self.validator.validate_input("abc xyz")
        
        assert result.is_valid is False
        assert any(error.code == "WEIGHT_003" for error in result.errors)
    
    def test_validate_negative_weight(self):
        """Test validation of negative weight"""
        result = self.validator.validate_input("-5 kg")
        
        assert result.is_valid is False
        assert any(error.code == "WEIGHT_005" for error in result.errors)
    
    def test_validate_unsupported_unit(self):
        """Test validation with unsupported unit"""
        result = self.validator.validate_input("5 xyz")
        
        assert result.is_valid is False
        assert any(error.code == "WEIGHT_008" for error in result.errors)
    
    def test_validate_weight_too_small(self):
        """Test validation of weight below minimum"""
        result = self.validator.validate_input("0.0001 mg")
        
        assert result.is_valid is False
        assert any(error.code == "WEIGHT_006" for error in result.errors)
    
    def test_validate_weight_too_large(self):
        """Test validation of weight above maximum"""
        result = self.validator.validate_input("10000000 kg")
        
        assert result.is_valid is False
        assert any(error.code == "WEIGHT_007" for error in result.errors)


class TestWeightConverter:
    """Test weight conversion functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.converter = WeightConverter()
    
    def test_convert_same_unit(self):
        """Test conversion within same unit"""
        result = self.converter.convert(Decimal('5'), WeightUnit.KILOGRAM, WeightUnit.KILOGRAM)
        assert result == Decimal('5')
    
    def test_convert_kg_to_pounds(self):
        """Test kilogram to pound conversion"""
        result = self.converter.convert(Decimal('1'), WeightUnit.KILOGRAM, WeightUnit.POUND)
        expected = Decimal('2.204623')
        assert abs(result - expected) < Decimal('0.000001')
    
    def test_convert_pounds_to_kg(self):
        """Test pound to kilogram conversion"""
        result = self.converter.convert(Decimal('2.204623'), WeightUnit.POUND, WeightUnit.KILOGRAM)
        expected = Decimal('1.0')
        assert abs(result - expected) < Decimal('0.000001')
    
    def test_convert_grams_to_kg(self):
        """Test gram to kilogram conversion"""
        result = self.converter.convert(Decimal('1000'), WeightUnit.GRAM, WeightUnit.KILOGRAM)
        assert result == Decimal('1.000000')
    
    def test_convert_to_kg(self):
        """Test conversion to kilograms"""
        result = self.converter.convert_to_kg(Decimal('1'), WeightUnit.POUND)
        expected = Decimal('0.453592')
        assert abs(result - expected) < Decimal('0.000001')
    
    def test_convert_from_kg(self):
        """Test conversion from kilograms"""
        result = self.converter.convert_from_kg(Decimal('1'), WeightUnit.POUND)
        expected = Decimal('2.204623')
        assert abs(result - expected) < Decimal('0.000001')
    
    def test_get_conversion_factor(self):
        """Test getting conversion factor"""
        factor = self.converter.get_conversion_factor(WeightUnit.KILOGRAM, WeightUnit.GRAM)
        assert factor == Decimal('1000')
    
    def test_conversion_precision(self):
        """Test conversion maintains precision"""
        original = Decimal('1.234567')
        pounds = self.converter.convert(original, WeightUnit.KILOGRAM, WeightUnit.POUND)
        back_to_kg = self.converter.convert(pounds, WeightUnit.POUND, WeightUnit.KILOGRAM)
        
        assert abs(original - back_to_kg) < Decimal('0.000001')


class TestUnitValidator:
    """Test unit validation and normalization"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.validator = UnitValidator()
    
    def test_normalize_standard_units(self):
        """Test normalization of standard units"""
        assert self.validator.normalize_unit("kg") == WeightUnit.KILOGRAM
        assert self.validator.normalize_unit("lbs") == WeightUnit.POUND
        assert self.validator.normalize_unit("g") == WeightUnit.GRAM
    
    def test_normalize_case_insensitive(self):
        """Test case-insensitive normalization"""
        assert self.validator.normalize_unit("KG") == WeightUnit.KILOGRAM
        assert self.validator.normalize_unit("Lbs") == WeightUnit.POUND
        assert self.validator.normalize_unit("GRAM") == WeightUnit.GRAM
    
    def test_normalize_aliases(self):
        """Test normalization of unit aliases"""
        assert self.validator.normalize_unit("kilogram") == WeightUnit.KILOGRAM
        assert self.validator.normalize_unit("pounds") == WeightUnit.POUND
        assert self.validator.normalize_unit("ounce") == WeightUnit.OUNCE
    
    def test_normalize_invalid_unit(self):
        """Test normalization with invalid unit"""
        with pytest.raises(ValueError) as exc_info:
            self.validator.normalize_unit("xyz")
        
        assert "Unsupported weight unit" in str(exc_info.value)


class TestWeightNormalizer:
    """Test weight normalization functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = SimpleConfig()
        self.normalizer = WeightNormalizer(self.config)
    
    def test_normalize_basic_input(self):
        """Test basic weight normalization"""
        result = self.normalizer.normalize_weight_input("5 kg")
        
        assert isinstance(result, NormalizedWeight)
        assert result.original_input == "5 kg"
        assert result.weight_kg == Decimal('5.000000')
        assert result.parsed_unit == WeightUnit.KILOGRAM
        assert result.confidence == 1.0
    
    def test_normalize_with_conversion(self):
        """Test normalization with unit conversion"""
        result = self.normalizer.normalize_weight_input("2.2 lbs")
        
        assert result.original_input == "2.2 lbs"
        assert result.parsed_unit == WeightUnit.POUND
        assert abs(result.weight_kg - Decimal('0.997903')) < Decimal('0.000001')
    
    def test_normalize_invalid_input(self):
        """Test normalization with invalid input"""
        with pytest.raises(WeightValidationException):
            self.normalizer.normalize_weight_input("invalid")


class TestAIProviderWeightRanges:
    """Test AI provider weight ranges functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.ai_ranges = AIProviderWeightRanges()
    
    def test_get_weight_category_light(self):
        """Test weight category for light objects"""
        category = self.ai_ranges.get_weight_category(Decimal('0.5'))
        assert category == 'light'
    
    def test_get_weight_category_medium(self):
        """Test weight category for medium objects"""
        category = self.ai_ranges.get_weight_category(Decimal('50'))
        assert category == 'medium'
    
    def test_get_weight_category_heavy(self):
        """Test weight category for heavy objects"""
        category = self.ai_ranges.get_weight_category(Decimal('5000'))
        assert category == 'heavy'
    
    def test_get_weight_category_extreme(self):
        """Test weight category for extreme weights"""
        category = self.ai_ranges.get_weight_category(Decimal('10000000'))
        assert category == 'extreme'
    
    def test_get_comparable_objects(self):
        """Test getting comparable objects"""
        objects = self.ai_ranges.get_comparable_objects(Decimal('0.5'))
        assert isinstance(objects, list)
        assert len(objects) > 0
        
        expected_objects = ['smartphones', 'books', 'laptops', 'cats']
        assert any(obj in objects for obj in expected_objects)
    
    def test_get_preferred_unit(self):
        """Test getting preferred unit for category"""
        unit = self.ai_ranges.get_preferred_unit(Decimal('0.5'))
        assert unit == WeightUnit.KILOGRAM
        
        unit = self.ai_ranges.get_preferred_unit(Decimal('5000'))
        assert unit == WeightUnit.METRIC_TON


class TestWeightFormatter:
    """Test weight formatting functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = SimpleConfig()
        self.formatter = WeightFormatter(self.config)
    
    def test_format_for_default_locale(self):
        """Test formatting for default locale"""
        result = self.formatter.format_for_locale(Decimal('5.5'))
        assert 'kg' in result
        assert '5.5' in result
    
    def test_format_for_us_locale(self):
        """Test formatting for US locale"""
        result = self.formatter.format_for_locale(Decimal('1'), 'US')
        assert 'lb' in result or 'lbs' in result
    
    def test_format_with_separators(self):
        """Test formatting with thousands separators"""
        result = self.formatter._format_with_separators(Decimal('1000.5'), WeightUnit.KILOGRAM)
        assert '1,000.5' in result
        assert 'kg' in result


class TestEdgeCaseHandler:
    """Test edge case handling functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.handler = EdgeCaseHandler()
    
    def test_handle_normal_weights(self):
        """Test handling of normal weight values"""
        result = self.handler.handle_extreme_weights(Decimal('5'))
        
        assert result.adjusted_weight == Decimal('5')
        assert result.is_extreme is False
        assert len(result.warnings) == 0
    
    def test_handle_very_small_weights(self):
        """Test handling of very small weights"""
        result = self.handler.handle_extreme_weights(Decimal('0.0000001'))
        
        assert result.is_extreme is True
        assert len(result.warnings) > 0
        assert "extremely small" in result.warnings[0]
    
    def test_handle_very_large_weights(self):
        """Test handling of very large weights"""
        result = self.handler.handle_extreme_weights(Decimal('1e16'))
        
        assert result.is_extreme is True
        assert len(result.warnings) > 0
        assert "astronomical scales" in result.warnings[0]
    
    def test_handle_precision_limits(self):
        """Test handling of precision limits"""
        value = Decimal('1.1234567890')
        result = self.handler.handle_precision_limits(value)
        
        assert str(result).count('.') <= 1
        if '.' in str(result):
            decimal_places = len(str(result).split('.')[1])
            assert decimal_places <= 6


class TestPrecisionManager:
    """Test precision management functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.manager = PrecisionManager()
    
    def test_quantize_for_display(self):
        """Test quantization for display"""
        value = Decimal('1.23456789')
        result = self.manager.quantize_for_display(value, WeightUnit.KILOGRAM)
        
        decimal_str = str(result)
        if '.' in decimal_str:
            decimal_places = len(decimal_str.split('.')[1])
            assert decimal_places <= 3
    
    def test_check_precision_loss_none(self):
        """Test precision loss detection with no loss"""
        original = Decimal('1.000000')
        processed = Decimal('1.000000')
        
        assert self.manager.check_precision_loss(original, processed) is False
    
    def test_check_precision_loss_detected(self):
        """Test precision loss detection with loss"""
        original = Decimal('1.000000')
        processed = Decimal('1.001000')
        assert self.manager.check_precision_loss(original, processed) is True


class TestWeightProcessingExceptions:
    """Test weight processing exceptions"""
    
    def test_weight_validation_exception(self):
        """Test WeightValidationException"""
        errors = [ValidationError(
            code="WEIGHT_001",
            message="Test error",
            category="client_error",
            field="test_field"
        )]
        
        exception = WeightValidationException(errors)
        assert len(exception.errors) == 1
        assert "validation failed" in str(exception)
    
    def test_weight_conversion_exception(self):
        """Test WeightConversionException"""
        exception = WeightConversionException("Conversion failed")
        assert "Conversion failed" in str(exception)


class TestWeightErrorCodes:
    """Test weight error codes"""
    
    def test_error_codes_complete(self):
        """Test that all error codes are defined"""
        required_codes = [
            "WEIGHT_001", "WEIGHT_002", "WEIGHT_003", "WEIGHT_004",
            "WEIGHT_005", "WEIGHT_006", "WEIGHT_007", "WEIGHT_008"
        ]
        
        for code in required_codes:
            assert code in WEIGHT_ERROR_CODES
    
    def test_error_code_messages(self):
        """Test error code messages are meaningful"""
        assert WEIGHT_ERROR_CODES["WEIGHT_001"] == "Empty weight input"
        assert WEIGHT_ERROR_CODES["WEIGHT_003"] == "Unparseable weight format"
        assert WEIGHT_ERROR_CODES["WEIGHT_005"] == "Non-positive weight"


class TestWeightProcessorIntegration:
    """Integration tests with realistic weight processing scenarios"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.processor = WeightProcessor()
    
    def test_realistic_weight_scenarios(self):
        """Test realistic weight processing scenarios"""
        test_cases = [
            ("5 kg", WeightUnit.KILOGRAM, Decimal('5')),
            ("2.2 lbs", WeightUnit.POUND, Decimal('0.997903')),
            ("1000 g", WeightUnit.GRAM, Decimal('1')),
            ("16 oz", WeightUnit.OUNCE, Decimal('0.453592')),
            ("1 stone", WeightUnit.STONE, Decimal('6.350293')),
        ]
        
        for input_str, expected_unit, expected_kg_approx in test_cases:
            result = self.processor.process_weight(input_str)
            
            assert result.original_input == input_str
            assert result.unit_used == expected_unit
            assert abs(result.weight_kg - expected_kg_approx) < Decimal('0.000001')
            assert result.confidence > 0.5
    
    def test_end_to_end_processing(self):
        """Test complete end-to-end weight processing"""
        result = self.processor.process_weight("5.5 lbs")
        
        assert isinstance(result, WeightItem)
        assert result.weight_kg > 0
        assert result.weight_display is not None
        assert result.unit_used == WeightUnit.POUND
        
        category = self.processor.get_weight_category(result.weight_kg)
        objects = self.processor.get_comparable_objects(result.weight_kg)
        
        assert isinstance(category, str)
        assert isinstance(objects, list)
        assert len(objects) > 0
    
    def test_error_handling_integration(self):
        """Test integrated error handling"""
        error_inputs = [
            "",
            "abc",
            "-5 kg",
            "0 kg",
            "5 xyz",
        ]
        
        for error_input in error_inputs:
            with pytest.raises(WeightValidationException):
                self.processor.process_weight(error_input)