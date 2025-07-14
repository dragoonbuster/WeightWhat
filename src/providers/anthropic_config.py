"""
Configuration utilities for the Anthropic provider.

This module provides helper functions for configuring the Anthropic provider
with appropriate defaults and validation.
"""

import os
from typing import Dict, Any, Optional
from enum import Enum


class AnthropicModel(str, Enum):
    """Available Anthropic Claude models."""
    OPUS = "claude-3-opus-20240229"
    SONNET = "claude-3-sonnet-20240229"
    HAIKU = "claude-3-haiku-20240307"


class AnthropicConfigBuilder:
    """Builder for Anthropic provider configuration."""
    
    def __init__(self):
        """Initialize with default configuration."""
        self._config = {
            # Core settings
            'api_key': None,
            'model': AnthropicModel.SONNET,
            'base_url': 'https://api.anthropic.com',
            
            # Request parameters
            'timeout_seconds': 60.0,
            'max_tokens': 1024,
            'temperature': 0.7,
            'top_p': 1.0,
            'top_k': 0,
            
            # Rate limiting
            'rate_limit_rpm': 1000,
            
            # Anthropic-specific features
            'intelligent_model_selection': True,
            'use_xml_tags': True,
            'safety_enabled': True,
            'beta_features': False,
            
            # Circuit breaker
            'circuit_breaker_failure_threshold': 5,
            'circuit_breaker_recovery_timeout': 60,
            
            # Monitoring
            'enable_debug_logging': False,
            'track_token_usage': True
        }
    
    def with_api_key(self, api_key: str) -> 'AnthropicConfigBuilder':
        """Set API key."""
        self._config['api_key'] = api_key
        return self
    
    def with_model(self, model: AnthropicModel) -> 'AnthropicConfigBuilder':
        """Set Claude model."""
        self._config['model'] = model.value
        return self
    
    def with_intelligent_selection(self, enabled: bool = True) -> 'AnthropicConfigBuilder':
        """Enable/disable intelligent model selection."""
        self._config['intelligent_model_selection'] = enabled
        return self
    
    def with_xml_tags(self, enabled: bool = True) -> 'AnthropicConfigBuilder':
        """Enable/disable XML tag formatting for better Claude performance."""
        self._config['use_xml_tags'] = enabled
        return self
    
    def with_safety(self, enabled: bool = True) -> 'AnthropicConfigBuilder':
        """Enable/disable safety filtering."""
        self._config['safety_enabled'] = enabled
        return self
    
    def with_beta_features(self, enabled: bool = False) -> 'AnthropicConfigBuilder':
        """Enable/disable beta features."""
        self._config['beta_features'] = enabled
        return self
    
    def with_temperature(self, temperature: float) -> 'AnthropicConfigBuilder':
        """Set generation temperature (0.0-1.0)."""
        if not 0.0 <= temperature <= 1.0:
            raise ValueError("Temperature must be between 0.0 and 1.0")
        self._config['temperature'] = temperature
        return self
    
    def with_max_tokens(self, max_tokens: int) -> 'AnthropicConfigBuilder':
        """Set maximum output tokens."""
        if max_tokens < 1 or max_tokens > 4096:
            raise ValueError("Max tokens must be between 1 and 4096")
        self._config['max_tokens'] = max_tokens
        return self
    
    def with_timeout(self, timeout_seconds: float) -> 'AnthropicConfigBuilder':
        """Set request timeout."""
        if timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")
        self._config['timeout_seconds'] = timeout_seconds
        return self
    
    def with_rate_limit(self, rpm: int) -> 'AnthropicConfigBuilder':
        """Set rate limit (requests per minute)."""
        if rpm <= 0:
            raise ValueError("Rate limit must be positive")
        self._config['rate_limit_rpm'] = rpm
        return self
    
    def with_circuit_breaker(
        self, 
        failure_threshold: int = 5, 
        recovery_timeout: int = 60
    ) -> 'AnthropicConfigBuilder':
        """Configure circuit breaker settings."""
        if failure_threshold <= 0:
            raise ValueError("Failure threshold must be positive")
        if recovery_timeout <= 0:
            raise ValueError("Recovery timeout must be positive")
        
        self._config['circuit_breaker_failure_threshold'] = failure_threshold
        self._config['circuit_breaker_recovery_timeout'] = recovery_timeout
        return self
    
    def with_debug_logging(self, enabled: bool = True) -> 'AnthropicConfigBuilder':
        """Enable/disable debug logging."""
        self._config['enable_debug_logging'] = enabled
        return self
    
    def from_environment(self) -> 'AnthropicConfigBuilder':
        """Load configuration from environment variables."""
        # Core settings
        if api_key := os.getenv('SIZECOMPARATOR_ANTHROPIC_API_KEY'):
            self._config['api_key'] = api_key
        
        if model := os.getenv('SIZECOMPARATOR_ANTHROPIC_MODEL'):
            self._config['model'] = model
        
        if base_url := os.getenv('SIZECOMPARATOR_ANTHROPIC_ENDPOINT'):
            self._config['base_url'] = base_url
        
        # Request parameters
        if timeout := os.getenv('SIZECOMPARATOR_ANTHROPIC_TIMEOUT'):
            try:
                self._config['timeout_seconds'] = float(timeout)
            except ValueError:
                pass
        
        if max_tokens := os.getenv('SIZECOMPARATOR_ANTHROPIC_MAX_TOKENS'):
            try:
                self._config['max_tokens'] = int(max_tokens)
            except ValueError:
                pass
        
        if temperature := os.getenv('SIZECOMPARATOR_ANTHROPIC_TEMPERATURE'):
            try:
                self._config['temperature'] = float(temperature)
            except ValueError:
                pass
        
        # Feature flags
        if beta_features := os.getenv('SIZECOMPARATOR_ANTHROPIC_BETA_FEATURES'):
            self._config['beta_features'] = beta_features.lower() in ('true', '1', 'yes')
        
        if debug := os.getenv('SIZECOMPARATOR_DEBUG'):
            self._config['enable_debug_logging'] = debug.lower() in ('true', '1', 'yes')
        
        return self
    
    def build(self) -> Dict[str, Any]:
        """Build and validate the configuration."""
        config = self._config.copy()
        
        # Validate required settings
        if not config['api_key']:
            raise ValueError(
                "API key is required. Set SIZECOMPARATOR_ANTHROPIC_API_KEY "
                "environment variable or call with_api_key()"
            )
        
        # Validate model
        valid_models = [model.value for model in AnthropicModel]
        if config['model'] not in valid_models:
            raise ValueError(f"Invalid model. Must be one of: {valid_models}")
        
        # Validate numeric ranges
        if not 0.0 <= config['temperature'] <= 1.0:
            raise ValueError("Temperature must be between 0.0 and 1.0")
        
        if not 1 <= config['max_tokens'] <= 4096:
            raise ValueError("Max tokens must be between 1 and 4096")
        
        if config['timeout_seconds'] <= 0:
            raise ValueError("Timeout must be positive")
        
        if config['rate_limit_rpm'] <= 0:
            raise ValueError("Rate limit must be positive")
        
        return config


def get_default_config() -> Dict[str, Any]:
    """Get default Anthropic provider configuration."""
    return AnthropicConfigBuilder().from_environment().build()


def get_production_config() -> Dict[str, Any]:
    """Get production-optimized Anthropic provider configuration."""
    return (AnthropicConfigBuilder()
            .from_environment()
            .with_model(AnthropicModel.SONNET)  # Good balance of cost/performance
            .with_intelligent_selection(True)
            .with_xml_tags(True)
            .with_safety(True)
            .with_beta_features(False)
            .with_temperature(0.7)
            .with_timeout(30.0)  # Shorter timeout for production
            .with_circuit_breaker(failure_threshold=3, recovery_timeout=60)
            .with_debug_logging(False)
            .build())


def get_development_config() -> Dict[str, Any]:
    """Get development-optimized Anthropic provider configuration."""
    return (AnthropicConfigBuilder()
            .from_environment()
            .with_model(AnthropicModel.HAIKU)  # Fastest and cheapest for dev
            .with_intelligent_selection(False)  # Consistent for testing
            .with_xml_tags(True)
            .with_safety(True)
            .with_beta_features(True)  # Test new features
            .with_temperature(0.5)  # More deterministic
            .with_timeout(60.0)  # Longer timeout for debugging
            .with_circuit_breaker(failure_threshold=5, recovery_timeout=30)
            .with_debug_logging(True)
            .build())


def get_cost_optimized_config() -> Dict[str, Any]:
    """Get cost-optimized Anthropic provider configuration."""
    return (AnthropicConfigBuilder()
            .from_environment()
            .with_model(AnthropicModel.HAIKU)  # Cheapest model
            .with_intelligent_selection(False)  # Always use cheapest
            .with_xml_tags(True)
            .with_safety(True)
            .with_max_tokens(512)  # Limit output tokens
            .with_temperature(0.7)
            .build())


def get_performance_optimized_config() -> Dict[str, Any]:
    """Get performance-optimized Anthropic provider configuration."""
    return (AnthropicConfigBuilder()
            .from_environment()
            .with_model(AnthropicModel.OPUS)  # Most capable model
            .with_intelligent_selection(True)
            .with_xml_tags(True)
            .with_safety(True)
            .with_max_tokens(2048)  # Allow longer responses
            .with_temperature(0.8)  # More creative
            .with_timeout(120.0)  # Longer timeout for complex requests
            .build())