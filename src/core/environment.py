"""
Environment Management for SizeComparator

This module provides environment management functionality compatible with
the existing test suite and service factory.
"""

import os
from enum import Enum
from typing import Any, Optional, Dict
from .simple_config import SimpleConfig, get_config


class EnvironmentType(str, Enum):
    """Supported environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class EnvironmentManager:
    """Environment manager that wraps the simple config system"""
    
    def __init__(self, environment: Optional[EnvironmentType] = None):
        """Initialize environment manager"""
        self._config = get_config()
        self._environment = environment or self._detect_environment()
    
    def _detect_environment(self) -> EnvironmentType:
        """Detect environment from configuration"""
        env_str = self._config.get('environment', 'development')
        try:
            return EnvironmentType(env_str)
        except ValueError:
            return EnvironmentType.DEVELOPMENT
    
    @property
    def environment(self) -> EnvironmentType:
        """Get current environment"""
        return self._environment
    
    def get_variable(self, key: str, default: Any = None, mask_sensitive: bool = True) -> Any:
        """Get environment variable or configuration value"""
        # First try environment variable
        value = os.getenv(key)
        if value is not None:
            return value
        
        # Then try config system
        # Map common environment variable names to config keys
        key_mapping = {
            'SIZECOMPARATOR_OPENAI_API_KEY': 'openai_api_key',
            'SIZECOMPARATOR_ANTHROPIC_API_KEY': 'anthropic_api_key',
            'SIZECOMPARATOR_XAI_API_KEY': 'xai_api_key',
            'SIZECOMPARATOR_SERVICE_STRATEGY': 'service_strategy',
            'SIZECOMPARATOR_FORCE_BASIC_SERVICE': 'force_basic_service',
            'SIZECOMPARATOR_REQUIRE_VALIDATION': 'require_validation',
        }
        
        config_key = key_mapping.get(key, key.lower().replace('sizecomparator_', ''))
        return self._config.get(config_key, default)
    
    def is_development(self) -> bool:
        """Check if running in development"""
        return self._environment == EnvironmentType.DEVELOPMENT
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self._environment == EnvironmentType.PRODUCTION
    
    def is_staging(self) -> bool:
        """Check if running in staging"""
        return self._environment == EnvironmentType.STAGING