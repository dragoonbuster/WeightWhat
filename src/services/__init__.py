"""
Services module for SizeComparator

This module contains all business logic services including weight processing,
configuration management, and AI provider integration.
"""

from .weight_processor import (
    WeightProcessor,
    WeightUnit,
    WeightItem,
    WeightRange,
    ValidationResult,
    ValidationError,
    ValidationWarning,
    ConversionResult,
    NormalizedWeight,
    ProcessingMetadata,
    WeightValidationException,
    WeightConversionException,
    WeightProcessingException,
    create_weight_processor,
    WEIGHT_ERROR_CODES
)

__all__ = [
    "WeightProcessor",
    "WeightUnit", 
    "WeightItem",
    "WeightRange",
    "ValidationResult",
    "ValidationError",
    "ValidationWarning",
    "ConversionResult",
    "NormalizedWeight",
    "ProcessingMetadata",
    "WeightValidationException",
    "WeightConversionException", 
    "WeightProcessingException",
    "create_weight_processor",
    "WEIGHT_ERROR_CODES"
]