"""
AI Providers package for SizeComparator.

This package contains all AI provider implementations including:
- OpenAI Provider (GPT-4, GPT-3.5-turbo)
- Anthropic Provider (Claude 3 Opus, Sonnet, Haiku)
- Base provider interface and utilities
"""

from .base import (
    AIProviderBase,
    ProviderCapabilities,
    RetryConfig
)
from .factory import (
    ProviderFactory,
    ProviderRegistry,
    register_provider,
    get_provider
)

try:
    from .openai_provider import (
        OpenAIProvider,
        OpenAIRateLimiter,
        TokenUsageTracker,
        ResponseCache
    )
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .anthropic_provider import AnthropicProvider, ClaudeModel
from .anthropic_config import (
    AnthropicConfigBuilder,
    AnthropicModel,
    get_default_config,
    get_production_config,
    get_development_config,
    get_cost_optimized_config,
    get_performance_optimized_config
)

try:
    from .xai_provider import XAIProvider
    XAI_AVAILABLE = True
except ImportError:
    XAI_AVAILABLE = False

__all__ = [
    # Base classes and interfaces
    "AIProviderBase",
    "ProviderCapabilities", 
    "RetryConfig",
    
    # Factory and registration
    "ProviderFactory",
    "ProviderRegistry",
    "register_provider",
    "get_provider",
    
    # Anthropic provider
    "AnthropicProvider",
    "ClaudeModel",
    "AnthropicConfigBuilder",
    "AnthropicModel",
    "get_default_config",
    "get_production_config", 
    "get_development_config",
    "get_cost_optimized_config",
    "get_performance_optimized_config",
]

# Add OpenAI exports if available
if OPENAI_AVAILABLE:
    __all__.extend([
        "OpenAIProvider",
        "OpenAIRateLimiter",
        "TokenUsageTracker",
        "ResponseCache"
    ])

# Add XAI exports if available
if XAI_AVAILABLE:
    __all__.extend([
        "XAIProvider"
    ])