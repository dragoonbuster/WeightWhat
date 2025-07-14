"""
Shared types for Comparison Service

Common types and enums used across comparison service components.
"""

from decimal import Decimal
from enum import Enum

from ...services.weight_processor import WeightUnit


class WeightCategory(str, Enum):
    """Weight categories for context determination"""
    MICROSCOPIC = "microscopic"      # < 1mg
    VERY_LIGHT = "very_light"       # 1mg - 100mg  
    LIGHT = "light"                 # 100mg - 10kg
    MEDIUM = "medium"               # 10kg - 1000kg
    HEAVY = "heavy"                 # 1000kg - 100 tons
    MASSIVE = "massive"             # > 100 tons


class UnitSystem(str, Enum):
    """Unit systems for locale preference"""
    METRIC = "metric"
    IMPERIAL = "imperial"


class WeightContext:
    """Context information about a weight"""
    def __init__(
        self,
        category: WeightCategory,
        scale_context: str,
        measurement_context: str,
        original_unit: WeightUnit,
        is_metric: bool
    ):
        self.category = category
        self.scale_context = scale_context
        self.measurement_context = measurement_context
        self.original_unit = original_unit
        self.is_metric = is_metric


class ComparisonObject:
    """Object used for weight comparison"""
    def __init__(
        self,
        name: str,
        weight_kg: Decimal,
        description: str,
        category: str
    ):
        self.name = name
        self.weight_kg = weight_kg
        self.description = description
        self.category = category


class ComparisonMetadata:
    """Metadata about a comparison response"""
    def __init__(
        self,
        provider_used: str,
        model_used: str,
        response_time_ms: int,
        cache_hit: bool,
        confidence_score: float,
        comparison_style: str,
        locale: str,
        generated_at: str,
        is_fallback: bool = False
    ):
        self.provider_used = provider_used
        self.model_used = model_used
        self.response_time_ms = response_time_ms
        self.cache_hit = cache_hit
        self.confidence_score = confidence_score
        self.comparison_style = comparison_style
        self.locale = locale
        self.generated_at = generated_at
        self.is_fallback = is_fallback


class WeightComparisonResponse:
    """Response from weight comparison service"""
    def __init__(
        self,
        comparison_text: str,
        weight_value: Decimal,
        weight_unit: WeightUnit,
        weight_in_kg: Decimal,
        weight_category: WeightCategory,
        comparison_objects: list[str],
        visualization_prompt: str = None,
        metadata: ComparisonMetadata = None,
        related_weights: list[dict] = None,
        fun_facts: list[str] = None
    ):
        self.comparison_text = comparison_text
        self.weight_value = weight_value
        self.weight_unit = weight_unit
        self.weight_in_kg = weight_in_kg
        self.weight_category = weight_category
        self.comparison_objects = comparison_objects
        self.visualization_prompt = visualization_prompt
        self.metadata = metadata
        self.related_weights = related_weights or []
        self.fun_facts = fun_facts or []