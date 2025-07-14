#!/usr/bin/env python3
"""
Demo script showing WeightProcessor functionality

This script demonstrates the comprehensive weight processing capabilities
of the SizeComparator WeightProcessor component.
"""

from decimal import Decimal
from src.services.weight_processor import (
    WeightProcessor,
    WeightUnit,
    WeightValidationException,
    create_weight_processor
)


def demo_basic_processing():
    """Demonstrate basic weight processing"""
    print("=== Basic Weight Processing ===")
    processor = create_weight_processor()
    
    test_inputs = [
        "5 kg",
        "10.5 lbs", 
        "2000 g",
        "16 oz",
        "1 stone",
        "1.5 metric tons"
    ]
    
    for weight_input in test_inputs:
        try:
            result = processor.process_weight(weight_input)
            print(f"Input: '{weight_input}'")
            print(f"  -> {result.weight_kg} kg ({result.weight_display})")
            print(f"  -> Category: {processor.get_weight_category(result.weight_kg)}")
            print(f"  -> Comparable objects: {', '.join(processor.get_comparable_objects(result.weight_kg)[:3])}")
            print()
        except WeightValidationException as e:
            print(f"Input: '{weight_input}' -> VALIDATION ERROR: {e}")
            print()


def demo_unit_conversion():
    """Demonstrate unit conversion capabilities"""
    print("=== Unit Conversion ===")
    processor = create_weight_processor()
    
    # Convert 1 kg to various units
    weight_kg = Decimal('1')
    units_to_convert = [
        WeightUnit.POUND,
        WeightUnit.OUNCE,
        WeightUnit.GRAM,
        WeightUnit.STONE,
        WeightUnit.METRIC_TON
    ]
    
    print(f"Converting 1 kg to various units:")
    for unit in units_to_convert:
        result = processor.convert_weight(weight_kg, WeightUnit.KILOGRAM, unit)
        print(f"  1 kg = {result.converted_value} {unit.value}")
    print()


def demo_validation():
    """Demonstrate validation capabilities"""
    print("=== Validation Examples ===")
    processor = create_weight_processor()
    
    test_cases = [
        # Valid cases
        ("5.5 kg", True),
        ("2.2 pounds", True),
        ("1000 grams", True),
        
        # Invalid cases  
        ("", False),
        ("abc xyz", False),
        ("-5 kg", False),
        ("0 kg", False),
        ("5 invalid_unit", False),
    ]
    
    for weight_input, should_be_valid in test_cases:
        try:
            validation_result = processor.validate_weight_input(weight_input)
            status = "VALID" if validation_result.is_valid else "INVALID"
            expected = "VALID" if should_be_valid else "INVALID"
            match = "✓" if (validation_result.is_valid == should_be_valid) else "✗"
            
            print(f"{match} '{weight_input}' -> {status} (expected {expected})")
            
            if not validation_result.is_valid:
                for error in validation_result.errors[:1]:  # Show first error
                    print(f"    Error: {error.message}")
                    
        except Exception as e:
            print(f"✗ '{weight_input}' -> ERROR: {e}")
    print()


def demo_edge_cases():
    """Demonstrate edge case handling"""
    print("=== Edge Case Handling ===")
    processor = create_weight_processor()
    
    edge_cases = [
        "0.001 mg",  # Very small weight
        "1000000 kg",  # Very large weight  
        "1.234567890 kg",  # High precision
    ]
    
    for weight_input in edge_cases:
        try:
            result = processor.process_weight(weight_input)
            print(f"'{weight_input}' -> {result.weight_kg} kg")
            print(f"  Category: {processor.get_weight_category(result.weight_kg)}")
        except WeightValidationException as e:
            print(f"'{weight_input}' -> VALIDATION ERROR")
            for error in e.errors[:1]:
                print(f"  {error.message}")
        except Exception as e:
            print(f"'{weight_input}' -> ERROR: {e}")
    print()


def demo_ai_integration():
    """Demonstrate AI provider integration features"""
    print("=== AI Provider Integration ===")
    processor = create_weight_processor()
    
    test_weights = [
        Decimal('0.5'),      # Light category
        Decimal('50'),       # Medium category  
        Decimal('5000'),     # Heavy category
        Decimal('0.0001'),   # Very light category
    ]
    
    for weight_kg in test_weights:
        category = processor.get_weight_category(weight_kg)
        objects = processor.get_comparable_objects(weight_kg)
        weight_range = processor.get_weight_range_for_category(category)
        
        print(f"Weight: {weight_kg} kg")
        print(f"  Category: {category}")
        print(f"  Comparable objects: {', '.join(objects)}")
        if weight_range:
            print(f"  Category range: {weight_range.min_weight_kg} - {weight_range.max_weight_kg} kg")
            print(f"  Preferred unit: {weight_range.unit_preference}")
        print()


def demo_metrics():
    """Show processor metrics and capabilities"""
    print("=== Processor Metrics ===")
    processor = create_weight_processor()
    
    metrics = processor.get_processing_metrics()
    print(f"Internal precision: {metrics['internal_precision_places']} decimal places")
    print(f"Supported units: {metrics['supported_units_count']}")
    print(f"Weight categories: {metrics['weight_categories_count']}")
    print(f"Weight range: {metrics['min_weight_kg']} - {metrics['max_weight_kg']} kg")
    print()
    
    print("Supported units:")
    units = processor.get_supported_units()
    for i, unit in enumerate(sorted(units), 1):
        print(f"  {unit}", end="")
        if i % 8 == 0:  # New line every 8 units
            print()
        else:
            print(", ", end="")
    print("\n")


def main():
    """Run all demonstrations"""
    print("WeightProcessor Comprehensive Demo")
    print("=" * 50)
    print()
    
    demo_basic_processing()
    demo_unit_conversion()
    demo_validation()
    demo_edge_cases()
    demo_ai_integration()
    demo_metrics()
    
    print("Demo completed successfully! ✓")


if __name__ == "__main__":
    main()