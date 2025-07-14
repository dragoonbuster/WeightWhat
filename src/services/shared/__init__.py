"""
Shared components for AI provider management across all comparison services.

This module provides common interfaces, base classes, and utilities that can be
used by all comparison services (MVP, AI validation, fast validation, etc.).
"""

from .interfaces import (
    BaseComparisonService,
    AIProviderInterface,
    FallbackDataInterface,
    AIProviderConfig,
    AIProviderResponse,
)
from .ai_provider_manager import AIProviderManager
from .fallback_data import FallbackDataManager

__all__ = [
    "BaseComparisonService",
    "AIProviderInterface", 
    "FallbackDataInterface",
    "AIProviderConfig",
    "AIProviderResponse",
    "AIProviderManager",
    "FallbackDataManager",
]