"""
Weight Comparison Service for SizeComparator

Central orchestrator for weight comparisons, coordinating between weight processing,
AI provider selection, prompt generation, response processing, and caching.
"""

from .comparison_service import ComparisonService, create_comparison_service
from .types import (
    WeightComparisonResponse,
    WeightCategory,
    WeightContext,
    ComparisonObject,
    ComparisonMetadata
)
from .provider_selector import ProviderSelector
from .prompt_builder import PromptBuilder
from .response_processor import ResponseProcessor
from .cache_service import MemoryCache
from .provider_factory import SimpleAIProviderFactory

__all__ = [
    'ComparisonService',
    'create_comparison_service',
    'WeightComparisonResponse',
    'WeightCategory',
    'WeightContext',
    'ComparisonObject',
    'ComparisonMetadata',
    'ProviderSelector',
    'PromptBuilder',
    'ResponseProcessor',
    'MemoryCache',
    'SimpleAIProviderFactory'
]