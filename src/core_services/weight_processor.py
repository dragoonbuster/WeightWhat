"""
Simplified weight processing for SizeComparator.
Handles parsing, validation, and conversion of weight inputs.
"""

import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Tuple, List

# Standard weight units
UNITS = {
    'kg': 'kilogram',
    'lb': 'pound', 
    'g': 'gram',
    'oz': 'ounce',
    'mg': 'milligram',
    'ton': 'ton',
    'st': 'stone'
}

# Conversion factors to kg
TO_KG = {
    'kg': Decimal('1'),
    'g': Decimal('0.001'),
    'mg': Decimal('0.000001'),
    'lb': Decimal('0.453592'),
    'oz': Decimal('0.0283495'),
    'ton': Decimal('907.185'),
    'st': Decimal('6.35029')
}

# Unit aliases
UNIT_ALIASES = {
    # Kilogram
    'kg': 'kg', 'kgs': 'kg', 'kilogram': 'kg', 'kilograms': 'kg', 'kilo': 'kg', 'kilos': 'kg',
    # Pound
    'lb': 'lb', 'lbs': 'lb', 'pound': 'lb', 'pounds': 'lb', '#': 'lb',
    # Gram
    'g': 'g', 'gm': 'g', 'gms': 'g', 'gram': 'g', 'grams': 'g',
    # Ounce
    'oz': 'oz', 'ounce': 'oz', 'ounces': 'oz',
    # Milligram
    'mg': 'mg', 'milligram': 'mg', 'milligrams': 'mg',
    # Ton
    'ton': 'ton', 'tons': 'ton',
    # Stone
    'st': 'st', 'stone': 'st', 'stones': 'st'
}


def parse_weight(weight_input: str) -> Optional[Tuple[Decimal, str]]:
    """
    Parse weight input into numeric value and unit.
    Returns (value, unit) or None if invalid.
    """
    if not weight_input or not weight_input.strip():
        return None
    
    weight_input = weight_input.strip()
    
    # Simple pattern: number followed by unit
    pattern = r'^(-?\d+(?:\.\d+)?)\s*([a-zA-Z#]+)$'
    match = re.match(pattern, weight_input)
    
    if not match:
        return None
    
    try:
        value = Decimal(match.group(1))
        unit = match.group(2).lower()
        
        # Normalize unit
        if unit in UNIT_ALIASES:
            unit = UNIT_ALIASES[unit]
        else:
            return None
        
        # Validate positive
        if value <= 0:
            return None
            
        return (value, unit)
    except:
        return None


def convert_to_kg(value: Decimal, unit: str) -> Decimal:
    """Convert any weight to kilograms."""
    if unit not in TO_KG:
        raise ValueError(f"Unknown unit: {unit}")
    return value * TO_KG[unit]


def format_weight(value: Decimal, unit: str) -> str:
    """Format weight for display."""
    # Round to reasonable precision
    if value < 1:
        rounded = value.quantize(Decimal('0.001'))
    elif value < 100:
        rounded = value.quantize(Decimal('0.01'))
    else:
        rounded = value.quantize(Decimal('0.1'))
    
    # Remove trailing zeros
    rounded = rounded.normalize()
    
    return f"{rounded} {unit}"


class WeightProcessor:
    """Simple weight processor for the application."""
    
    def process(self, weight_input: str) -> Optional[Dict]:
        """
        Process weight input and return standardized result.
        Returns None if invalid.
        """
        parsed = parse_weight(weight_input)
        if not parsed:
            return None
        
        value, unit = parsed
        weight_kg = convert_to_kg(value, unit)
        
        # Check reasonable bounds (0.001g to 1000 tons)
        if weight_kg < Decimal('0.000001') or weight_kg > Decimal('1000000000'):
            return None
        
        return {
            'original_input': weight_input,
            'weight_kg': float(weight_kg),
            'display': format_weight(value, unit),
            'unit': unit,
            'value': float(value)
        }
    
    def validate(self, weight_input: str) -> bool:
        """Check if weight input is valid."""
        return parse_weight(weight_input) is not None
    
    def get_weight_category(self, weight_kg: float) -> str:
        """Get weight category for comparison context."""
        if weight_kg < 0.001:  # < 1g
            return 'microscopic'
        elif weight_kg < 0.1:  # < 100g
            return 'very_light'
        elif weight_kg < 10:  # < 10kg
            return 'light'
        elif weight_kg < 1000:  # < 1 ton
            return 'medium'
        elif weight_kg < 100000:  # < 100 tons
            return 'heavy'
        else:
            return 'very_heavy'