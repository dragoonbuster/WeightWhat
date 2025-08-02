"""
Services module - imports from core_services for backward compatibility.
"""

# Import from new location
from ..core_services import WeightProcessor, ComparisonEngine, CacheManager

__all__ = ['WeightProcessor', 'ComparisonEngine', 'CacheManager']