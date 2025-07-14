"""
Example configuration for X.ai (Grok) provider following XAI_PROVIDER_SPEC.md.

This module provides sample configurations for development, testing, and production
environments with appropriate rate limiting and quality validation settings.
"""

from typing import Dict, Any


def get_development_config() -> Dict[str, Any]:
    """Get development configuration for X.ai provider."""
    return {
        "api_config": {
            "endpoint": "https://api.x.ai/v1",
            "api_key": "${SIZECOMPARATOR_XAI_API_KEY}",
            "model": "grok-beta",
            "api_version": "v1"
        },
        "rate_limiting": {
            "requests_per_minute": 100,  # Conservative for development
            "burst_allowance": 20,
            "rate_limit_window": 60,
            "backoff_multiplier": 1.5
        },
        "reliability": {
            "timeout_seconds": 30,
            "max_retries": 3,
            "circuit_breaker": {
                "failure_threshold": 5,
                "recovery_timeout": 60,
                "half_open_calls": 2
            }
        },
        "quality_validation": {
            "min_confidence_threshold": 0.5,  # Lower for development
            "max_response_time_ms": 45000,
            "response_format_validation": "relaxed",
            "fallback_on_quality_issues": True
        },
        "response_processing": {
            "enable_response_normalization": True,
            "enable_quality_scoring": True,
            "enable_format_recovery": True,
            "max_recovery_attempts": 3
        }
    }


def get_production_config() -> Dict[str, Any]:
    """Get production configuration for X.ai provider."""
    return {
        "api_config": {
            "endpoint": "https://api.x.ai/v1",
            "api_key": "${SIZECOMPARATOR_XAI_API_KEY}",
            "model": "grok-beta",
            "api_version": "v1"
        },
        "rate_limiting": {
            "requests_per_minute": 450,  # Conservative production limit
            "burst_allowance": 30,
            "rate_limit_window": 60,
            "backoff_multiplier": 2.0
        },
        "reliability": {
            "timeout_seconds": 45,
            "max_retries": 1,  # Reduced retries for production
            "circuit_breaker": {
                "failure_threshold": 2,  # Lower threshold for production
                "recovery_timeout": 180,  # 3 minutes
                "half_open_calls": 1
            }
        },
        "quality_validation": {
            "min_confidence_threshold": 0.7,  # Higher for production
            "max_response_time_ms": 30000,
            "response_format_validation": "strict",
            "fallback_on_quality_issues": True
        },
        "response_processing": {
            "enable_response_normalization": True,
            "enable_quality_scoring": True,
            "enable_format_recovery": True,
            "max_recovery_attempts": 2  # Reduced attempts
        },
        "error_handling": {
            "enable_fallback": True,
            "max_fallback_attempts": 1,
            "fallback_delay_ms": 100
        },
        "monitoring": {
            "log_all_requests": False,  # Reduce log volume
            "track_quality_metrics": True,
            "alert_on_circuit_open": True
        }
    }


def get_test_config() -> Dict[str, Any]:
    """Get test configuration for X.ai provider."""
    return {
        "api_config": {
            "endpoint": "https://api.x.ai/v1",
            "api_key": "test_key_fake",
            "model": "grok-beta",
            "api_version": "v1"
        },
        "rate_limiting": {
            "requests_per_minute": 10,  # Very low for testing
            "burst_allowance": 5,
            "rate_limit_window": 60,
            "backoff_multiplier": 1.0
        },
        "reliability": {
            "timeout_seconds": 10,  # Short timeout for tests
            "max_retries": 1,
            "circuit_breaker": {
                "failure_threshold": 2,
                "recovery_timeout": 30,
                "half_open_calls": 1
            }
        },
        "quality_validation": {
            "min_confidence_threshold": 0.3,  # Very low for testing
            "max_response_time_ms": 15000,
            "response_format_validation": "relaxed",
            "fallback_on_quality_issues": False  # Don't use fallback in tests
        },
        "response_processing": {
            "enable_response_normalization": True,
            "enable_quality_scoring": False,  # Disable for simpler tests
            "enable_format_recovery": True,
            "max_recovery_attempts": 1
        }
    }


def get_cost_optimized_config() -> Dict[str, Any]:
    """Get cost-optimized configuration for X.ai provider."""
    return {
        "api_config": {
            "endpoint": "https://api.x.ai/v1",
            "api_key": "${SIZECOMPARATOR_XAI_API_KEY}",
            "model": "grok-beta",
            "api_version": "v1"
        },
        "rate_limiting": {
            "requests_per_minute": 200,  # Moderate rate to reduce costs
            "burst_allowance": 15,
            "rate_limit_window": 60,
            "backoff_multiplier": 3.0  # Longer waits to reduce retry costs
        },
        "reliability": {
            "timeout_seconds": 60,  # Longer timeout to avoid retries
            "max_retries": 1,  # Minimal retries
            "circuit_breaker": {
                "failure_threshold": 3,
                "recovery_timeout": 300,  # 5 minutes
                "half_open_calls": 1
            }
        },
        "quality_validation": {
            "min_confidence_threshold": 0.6,
            "max_response_time_ms": 60000,
            "response_format_validation": "relaxed",  # Accept more responses
            "fallback_on_quality_issues": False  # Don't use expensive fallbacks
        },
        "response_processing": {
            "enable_response_normalization": True,
            "enable_quality_scoring": False,  # Disable to save processing
            "enable_format_recovery": True,
            "max_recovery_attempts": 1  # Minimal recovery attempts
        }
    }


def get_performance_optimized_config() -> Dict[str, Any]:
    """Get performance-optimized configuration for X.ai provider."""
    return {
        "api_config": {
            "endpoint": "https://api.x.ai/v1",
            "api_key": "${SIZECOMPARATOR_XAI_API_KEY}",
            "model": "grok-beta",
            "api_version": "v1"
        },
        "rate_limiting": {
            "requests_per_minute": 500,  # Maximum allowed rate
            "burst_allowance": 50,
            "rate_limit_window": 60,
            "backoff_multiplier": 1.2  # Quick retries
        },
        "reliability": {
            "timeout_seconds": 20,  # Short timeout for speed
            "max_retries": 2,
            "circuit_breaker": {
                "failure_threshold": 5,
                "recovery_timeout": 30,  # Quick recovery
                "half_open_calls": 3
            }
        },
        "quality_validation": {
            "min_confidence_threshold": 0.5,  # Lower for speed
            "max_response_time_ms": 20000,
            "response_format_validation": "relaxed",
            "fallback_on_quality_issues": True
        },
        "response_processing": {
            "enable_response_normalization": True,
            "enable_quality_scoring": True,
            "enable_format_recovery": True,
            "max_recovery_attempts": 2
        }
    }