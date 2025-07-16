"""
Simple Configuration System for SizeComparator

This module provides a lightweight, environment-variable-based configuration
system that meets the actual needs of the application without unnecessary complexity.

Key Features:
- Environment variable loading with type conversion
- Simple fallback defaults
- Basic validation
- No hot-reload, no file watching, no complex hierarchies
- Production-ready security for sensitive values
"""

import os
import logging
from typing import Any, Dict, Optional, Union, List
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Supported environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class ConfigValue:
    """Configuration value with type and default."""
    key: str
    default: Any
    value_type: type
    description: str
    sensitive: bool = False


class SimpleConfig:
    """Simple configuration system using environment variables."""
    
    def __init__(self):
        """Initialize configuration system."""
        self._config: Dict[str, Any] = {}
        self._load_environment()
        
    def _load_environment(self):
        """Load environment variables and apply defaults."""
        # Core application settings
        self._config.update({
            'environment': self._get_env('SIZECOMPARATOR_ENV', 'development', str),
            'debug': self._get_env('SIZECOMPARATOR_DEBUG', False, bool),
            'log_level': self._get_env('SIZECOMPARATOR_LOG_LEVEL', 'INFO', str),
            
            # API settings
            'api_host': self._get_env('SIZECOMPARATOR_API_HOST', '0.0.0.0', str),
            'api_port': self._get_env('SIZECOMPARATOR_API_PORT', 8000, int),
            'api_workers': self._get_env('SIZECOMPARATOR_API_WORKERS', 1, int),
            
            # AI Provider - OpenAI
            'openai_api_key': self._get_env('SIZECOMPARATOR_OPENAI_API_KEY', None, str),
            'openai_model': self._get_env('SIZECOMPARATOR_OPENAI_MODEL', 'gpt-4', str),
            'openai_timeout': self._get_env('SIZECOMPARATOR_OPENAI_TIMEOUT', 30, int),
            'openai_max_tokens': self._get_env('SIZECOMPARATOR_OPENAI_MAX_TOKENS', 500, int),
            'openai_temperature': self._get_env('SIZECOMPARATOR_OPENAI_TEMPERATURE', 0.3, float),
            
            # AI Provider - Anthropic
            'anthropic_api_key': self._get_env('SIZECOMPARATOR_ANTHROPIC_API_KEY', None, str),
            'anthropic_model': self._get_env('SIZECOMPARATOR_ANTHROPIC_MODEL', 'claude-3-sonnet-20240229', str),
            'anthropic_timeout': self._get_env('SIZECOMPARATOR_ANTHROPIC_TIMEOUT', 60, int),
            'anthropic_max_tokens': self._get_env('SIZECOMPARATOR_ANTHROPIC_MAX_TOKENS', 1000, int),
            'anthropic_temperature': self._get_env('SIZECOMPARATOR_ANTHROPIC_TEMPERATURE', 0.0, float),
            
            # AI Provider - X.AI
            'xai_api_key': self._get_env('SIZECOMPARATOR_XAI_API_KEY', None, str),
            'xai_model': self._get_env('SIZECOMPARATOR_XAI_MODEL', 'grok-2', str),
            'xai_timeout': self._get_env('SIZECOMPARATOR_XAI_TIMEOUT', 45, int),
            
            # Cache settings
            'cache_provider': self._get_env('SIZECOMPARATOR_CACHE_PROVIDER', 'memory', str),
            'cache_ttl': self._get_env('SIZECOMPARATOR_CACHE_TTL', 3600, int),
            'cache_max_size': self._get_env('SIZECOMPARATOR_CACHE_MAX_SIZE', 1000, int),
            
            # Redis settings (if using Redis cache)
            'redis_host': self._get_env('SIZECOMPARATOR_REDIS_HOST', 'localhost', str),
            'redis_port': self._get_env('SIZECOMPARATOR_REDIS_PORT', 6379, int),
            'redis_db': self._get_env('SIZECOMPARATOR_REDIS_DB', 0, int),
            'redis_password': self._get_env('SIZECOMPARATOR_REDIS_PASSWORD', None, str),
            'redis_tls': self._get_env('SIZECOMPARATOR_REDIS_TLS', False, bool),
            
            # Service factory settings
            'service_strategy': self._get_env('SIZECOMPARATOR_SERVICE_STRATEGY', 'smart_routing', str),
            'force_basic_service': self._get_env('SIZECOMPARATOR_FORCE_BASIC_SERVICE', False, bool),
            'require_validation': self._get_env('SIZECOMPARATOR_REQUIRE_VALIDATION', True, bool),
            'service_timeout_ms': self._get_env('SIZECOMPARATOR_SERVICE_TIMEOUT_MS', 5000, int),
            
            # Security settings
            'secret_key': self._get_env('SIZECOMPARATOR_SECRET_KEY', 'dev-secret-key-change-in-production', str),
            
            # Feature flags
            'feature_enhanced_viz': self._get_env('SIZECOMPARATOR_FEATURE_ENHANCED_VIZ', True, bool),
            'feature_ai_suggestions': self._get_env('SIZECOMPARATOR_FEATURE_AI_SUGGESTIONS', False, bool),
            
            # Monitoring
            'metrics_enabled': self._get_env('SIZECOMPARATOR_METRICS_ENABLED', True, bool),
            'log_format': self._get_env('SIZECOMPARATOR_LOG_FORMAT', 'json', str),
        })
        
        # Validate configuration
        self._validate_config()
        
    def _get_env(self, key: str, default: Any, value_type: type) -> Any:
        """Get environment variable with type conversion."""
        value = os.getenv(key)
        
        if value is None:
            return default
            
        try:
            if value_type == bool:
                return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
            elif value_type == int:
                return int(value)
            elif value_type == float:
                return float(value)
            elif value_type == str:
                return value
            else:
                return value
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to convert {key}={value} to {value_type.__name__}: {e}")
            return default
            
    def _validate_config(self):
        """Validate configuration values."""
        # Ensure at least one AI provider is configured
        if not any([
            self._config.get('openai_api_key'),
            self._config.get('anthropic_api_key'),
            self._config.get('xai_api_key')
        ]):
            if self._config['environment'] == 'production':
                raise ValueError("At least one AI provider API key must be configured in production")
            else:
                logger.warning("No AI provider API keys configured - some features may not work")
                
        # Validate environment
        if self._config['environment'] not in ['development', 'staging', 'production']:
            logger.warning(f"Invalid environment: {self._config['environment']}, defaulting to development")
            self._config['environment'] = 'development'
            
        # Production security checks
        if self._config['environment'] == 'production':
            if self._config['secret_key'] == 'dev-secret-key-change-in-production':
                raise ValueError("SIZECOMPARATOR_SECRET_KEY must be changed in production")
                
        logger.info(f"Configuration loaded for {self._config['environment']} environment")
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config.get(key, default)
        
    def get_section(self, section: str, default: Any = None) -> Any:
        """Get configuration section (for backwards compatibility)."""
        # Handle dot notation for nested access
        if '.' in section:
            parts = section.split('.')
            value = self._config
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
            return value
        return self._config.get(section, default)
        
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values."""
        return self._config.copy()
        
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self._config['environment'] == 'development'
        
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self._config['environment'] == 'production'
        
    def get_ai_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get AI provider configuration."""
        if provider == 'openai':
            return {
                'api_key': self._config.get('openai_api_key'),
                'model': self._config.get('openai_model'),
                'timeout': self._config.get('openai_timeout'),
                'max_tokens': self._config.get('openai_max_tokens'),
                'temperature': self._config.get('openai_temperature'),
            }
        elif provider == 'anthropic':
            return {
                'api_key': self._config.get('anthropic_api_key'),
                'model': self._config.get('anthropic_model'),
                'timeout': self._config.get('anthropic_timeout'),
                'max_tokens': self._config.get('anthropic_max_tokens'),
                'temperature': self._config.get('anthropic_temperature'),
            }
        elif provider == 'xai':
            return {
                'api_key': self._config.get('xai_api_key'),
                'model': self._config.get('xai_model'),
                'timeout': self._config.get('xai_timeout'),
            }
        else:
            raise ValueError(f"Unknown AI provider: {provider}")
            
    def get_cache_config(self) -> Dict[str, Any]:
        """Get cache configuration."""
        return {
            'provider': self._config.get('cache_provider'),
            'ttl': self._config.get('cache_ttl'),
            'max_size': self._config.get('cache_max_size'),
            'host': self._config.get('redis_host'),
            'port': self._config.get('redis_port'),
            'db': self._config.get('redis_db'),
            'password': self._config.get('redis_password'),
            'tls': self._config.get('redis_tls'),
        }
        
    def get_api_config(self) -> Dict[str, Any]:
        """Get API server configuration."""
        return {
            'host': self._config.get('api_host'),
            'port': self._config.get('api_port'),
            'workers': self._config.get('api_workers'),
        }
        
    def get_service_config(self) -> Dict[str, Any]:
        """Get service factory configuration."""
        return {
            'strategy': self._config.get('service_strategy'),
            'force_basic': self._config.get('force_basic_service'),
            'require_validation': self._config.get('require_validation'),
            'timeout_ms': self._config.get('service_timeout_ms'),
        }
        
    def get_sanitized_config(self) -> Dict[str, Any]:
        """Get configuration with sensitive values masked."""
        sanitized = self._config.copy()
        
        # Mask sensitive values
        sensitive_keys = [
            'openai_api_key',
            'anthropic_api_key', 
            'xai_api_key',
            'redis_password',
            'secret_key'
        ]
        
        for key in sensitive_keys:
            if key in sanitized and sanitized[key]:
                value = str(sanitized[key])
                if len(value) > 8:
                    sanitized[key] = value[:4] + '*' * (len(value) - 8) + value[-4:]
                else:
                    sanitized[key] = '*' * len(value)
                    
        return sanitized


# Global configuration instance
_config_instance: Optional[SimpleConfig] = None


def get_config() -> SimpleConfig:
    """Get global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = SimpleConfig()
    return _config_instance


def reload_config() -> SimpleConfig:
    """Reload configuration from environment."""
    global _config_instance
    _config_instance = SimpleConfig()
    return _config_instance


# Convenience functions for common patterns
def get_env_or_config(env_key: str, config_key: str, default: Any = None) -> Any:
    """Get value from environment or config with fallback."""
    return os.getenv(env_key) or get_config().get(config_key, default)


def is_production() -> bool:
    """Check if running in production environment."""
    return get_config().is_production()


def is_development() -> bool:
    """Check if running in development environment."""
    return get_config().is_development()