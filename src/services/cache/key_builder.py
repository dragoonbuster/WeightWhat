"""
Cache key generation with hierarchical structure

This module provides intelligent cache key generation that supports:
- Hierarchical key structure for efficient invalidation
- Weight normalization for better cache hits
- Content-based hashing for deterministic keys
- Pattern-based key scanning and cleanup
"""

import hashlib
import json
import re
from typing import Dict, Any, Optional, List
from decimal import Decimal
from urllib.parse import quote
import logging

from src.models.weight import ProcessedWeight
from src.models.providers import AIProviderResponse

logger = logging.getLogger(__name__)


class CacheKeyBuilder:
    """Builds hierarchical cache keys with invalidation support."""
    
    SEPARATOR = ":"
    VERSION = "v1"
    MAX_KEY_LENGTH = 250  # Redis key length limit
    
    # Key prefixes for different data types
    PREFIXES = {
        "ai_response": "ai",
        "config": "cfg",
        "weight": "wgt",
        "template": "tpl",
        "feature_flag": "flag",
        "metrics": "met",
        "session": "sess",
        "temp": "tmp"
    }
    
    @classmethod
    def build_ai_response_key(
        cls,
        weight: ProcessedWeight,
        provider: str,
        model: str,
        prompt_hash: str,
        template_id: Optional[str] = None
    ) -> str:
        """
        Build key for AI response caching.
        
        Args:
            weight: Processed weight for normalization
            provider: AI provider name
            model: Model name
            prompt_hash: Hash of prompt content
            template_id: Optional template ID
            
        Returns:
            Hierarchical cache key
        """
        # Normalize weight for better cache hits
        normalized_weight = cls._normalize_weight(weight)
        
        # Truncate hash for key length management
        short_hash = prompt_hash[:12] if len(prompt_hash) > 12 else prompt_hash
        
        parts = [
            cls.PREFIXES["ai_response"],
            cls.VERSION,
            provider.lower(),
            model.lower().replace(".", "_").replace("-", "_"),
            short_hash,
            normalized_weight
        ]
        
        if template_id:
            parts.insert(-1, template_id[:20])  # Limit template ID length
        
        key = cls.SEPARATOR.join(parts)
        return cls._ensure_key_length(key)
    
    @classmethod
    def build_config_key(
        cls,
        config_type: str,
        version: str,
        environment: Optional[str] = None
    ) -> str:
        """
        Build key for configuration caching.
        
        Args:
            config_type: Type of configuration
            version: Configuration version
            environment: Optional environment name
            
        Returns:
            Configuration cache key
        """
        parts = [
            cls.PREFIXES["config"],
            config_type.lower(),
            version
        ]
        
        if environment:
            parts.append(environment.lower())
        
        key = cls.SEPARATOR.join(parts)
        return cls._ensure_key_length(key)
    
    @classmethod
    def build_weight_key(
        cls,
        weight_str: str,
        operation: str,
        context: Optional[str] = None
    ) -> str:
        """
        Build key for weight processing cache.
        
        Args:
            weight_str: Original weight string
            operation: Processing operation (e.g., "parsed", "converted")
            context: Optional context
            
        Returns:
            Weight processing cache key
        """
        # Normalize weight string for consistent keys
        normalized = cls._normalize_weight_string(weight_str)
        
        # Create hash for long weight strings
        if len(normalized) > 50:
            weight_hash = hashlib.md5(normalized.encode()).hexdigest()[:12]
            normalized = f"hash_{weight_hash}"
        
        parts = [
            cls.PREFIXES["weight"],
            operation.lower(),
            normalized
        ]
        
        if context:
            parts.append(context.lower()[:20])
        
        key = cls.SEPARATOR.join(parts)
        return cls._ensure_key_length(key)
    
    @classmethod
    def build_template_key(
        cls,
        template_id: str,
        variables_hash: str,
        version: Optional[str] = None
    ) -> str:
        """
        Build key for compiled template cache.
        
        Args:
            template_id: Template identifier
            variables_hash: Hash of template variables
            version: Optional template version
            
        Returns:
            Template cache key
        """
        parts = [
            cls.PREFIXES["template"],
            template_id[:30],  # Limit template ID length
            variables_hash[:12]  # Short hash for variables
        ]
        
        if version:
            parts.append(version)
        
        key = cls.SEPARATOR.join(parts)
        return cls._ensure_key_length(key)
    
    @classmethod
    def build_feature_flag_key(cls, flag_name: str) -> str:
        """
        Build key for feature flag cache.
        
        Args:
            flag_name: Feature flag name
            
        Returns:
            Feature flag cache key
        """
        normalized_name = flag_name.lower().replace("-", "_")
        return f"{cls.PREFIXES['feature_flag']}{cls.SEPARATOR}{normalized_name}"
    
    @classmethod
    def build_metrics_key(
        cls,
        metric_type: str,
        time_window: str,
        labels: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Build key for metrics cache.
        
        Args:
            metric_type: Type of metric
            time_window: Time window (e.g., "1h", "1d")
            labels: Optional metric labels
            
        Returns:
            Metrics cache key
        """
        parts = [
            cls.PREFIXES["metrics"],
            metric_type.lower(),
            time_window
        ]
        
        if labels:
            # Sort labels for consistent keys
            label_str = "_".join(f"{k}={v}" for k, v in sorted(labels.items()))
            label_hash = hashlib.md5(label_str.encode()).hexdigest()[:8]
            parts.append(label_hash)
        
        key = cls.SEPARATOR.join(parts)
        return cls._ensure_key_length(key)
    
    @classmethod
    def build_session_key(cls, session_id: str, data_type: str) -> str:
        """
        Build key for session data cache.
        
        Args:
            session_id: Session identifier
            data_type: Type of session data
            
        Returns:
            Session cache key
        """
        return f"{cls.PREFIXES['session']}{cls.SEPARATOR}{session_id}{cls.SEPARATOR}{data_type}"
    
    @classmethod
    def generate_content_hash(
        cls,
        content: Any,
        algorithm: str = "sha256"
    ) -> str:
        """
        Generate deterministic hash for cache key.
        
        Args:
            content: Content to hash (will be JSON serialized)
            algorithm: Hash algorithm to use
            
        Returns:
            Hexadecimal hash string
        """
        try:
            if isinstance(content, (dict, list)):
                # Sort keys for consistent hashing
                json_str = json.dumps(content, sort_keys=True, default=str)
            else:
                json_str = json.dumps(content, default=str)
            
            if algorithm == "md5":
                return hashlib.md5(json_str.encode()).hexdigest()
            elif algorithm == "sha1":
                return hashlib.sha1(json_str.encode()).hexdigest()
            else:  # default to sha256
                return hashlib.sha256(json_str.encode()).hexdigest()
                
        except Exception as e:
            logger.warning(f"Failed to hash content: {e}")
            # Fallback to string hash
            fallback_str = str(content)
            return hashlib.md5(fallback_str.encode()).hexdigest()
    
    @classmethod
    def generate_prompt_hash(
        cls,
        template: str,
        variables: Dict[str, Any]
    ) -> str:
        """
        Generate hash for AI prompt (template + variables).
        
        Args:
            template: Prompt template string
            variables: Template variables
            
        Returns:
            Hash of the complete prompt
        """
        # Normalize variables for consistent hashing
        normalized_vars = cls._normalize_prompt_variables(variables)
        
        prompt_data = {
            "template": template,
            "variables": normalized_vars
        }
        
        return cls.generate_content_hash(prompt_data, "sha256")
    
    @classmethod
    def parse_key_components(cls, key: str) -> Dict[str, str]:
        """
        Parse cache key into components.
        
        Args:
            key: Cache key to parse
            
        Returns:
            Dictionary of key components
        """
        parts = key.split(cls.SEPARATOR)
        
        if len(parts) < 2:
            return {"prefix": key, "type": "unknown"}
        
        prefix = parts[0]
        
        # Reverse lookup prefix
        key_type = None
        for type_name, type_prefix in cls.PREFIXES.items():
            if prefix == type_prefix:
                key_type = type_name
                break
        
        components = {
            "prefix": prefix,
            "type": key_type or "unknown",
            "parts": parts[1:],
            "full_key": key
        }
        
        # Type-specific parsing
        if key_type == "ai_response" and len(parts) >= 6:
            components.update({
                "version": parts[1],
                "provider": parts[2],
                "model": parts[3],
                "prompt_hash": parts[4],
                "weight": parts[5]
            })
        elif key_type == "config" and len(parts) >= 3:
            components.update({
                "config_type": parts[1],
                "version": parts[2],
                "environment": parts[3] if len(parts) > 3 else None
            })
        elif key_type == "weight" and len(parts) >= 3:
            components.update({
                "operation": parts[1],
                "weight_identifier": parts[2],
                "context": parts[3] if len(parts) > 3 else None
            })
        
        return components
    
    @classmethod
    def get_invalidation_patterns(cls, key_type: str, **filters) -> List[str]:
        """
        Get glob patterns for invalidating related keys.
        
        Args:
            key_type: Type of keys to invalidate
            **filters: Additional filters for pattern matching
            
        Returns:
            List of glob patterns
        """
        if key_type not in cls.PREFIXES:
            return []
        
        prefix = cls.PREFIXES[key_type]
        patterns = []
        
        if key_type == "ai_response":
            # Invalidate by provider
            if "provider" in filters:
                patterns.append(f"{prefix}{cls.SEPARATOR}*{cls.SEPARATOR}{filters['provider']}{cls.SEPARATOR}*")
            
            # Invalidate by model
            if "model" in filters:
                patterns.append(f"{prefix}{cls.SEPARATOR}*{cls.SEPARATOR}*{cls.SEPARATOR}{filters['model']}{cls.SEPARATOR}*")
            
            # Invalidate all AI responses
            patterns.append(f"{prefix}{cls.SEPARATOR}*")
            
        elif key_type == "config":
            # Invalidate by config type
            if "config_type" in filters:
                patterns.append(f"{prefix}{cls.SEPARATOR}{filters['config_type']}{cls.SEPARATOR}*")
            
            # Invalidate by environment
            if "environment" in filters:
                patterns.append(f"{prefix}{cls.SEPARATOR}*{cls.SEPARATOR}*{cls.SEPARATOR}{filters['environment']}")
            
            # Invalidate all configs
            patterns.append(f"{prefix}{cls.SEPARATOR}*")
            
        elif key_type == "weight":
            # Invalidate by operation
            if "operation" in filters:
                patterns.append(f"{prefix}{cls.SEPARATOR}{filters['operation']}{cls.SEPARATOR}*")
            
            # Invalidate all weight processing
            patterns.append(f"{prefix}{cls.SEPARATOR}*")
        
        return patterns
    
    @classmethod
    def _normalize_weight(cls, weight: ProcessedWeight) -> str:
        """Normalize weight for consistent cache keys."""
        # Round to 3 decimal places for cache efficiency
        kg_value = float(weight.parsed_value)
        rounded = round(kg_value, 3)
        
        # Use scientific notation for very large/small numbers
        if rounded >= 1000000 or (rounded > 0 and rounded < 0.001):
            return f"{rounded:.2e}kg"
        else:
            return f"{rounded}kg"
    
    @classmethod
    def _normalize_weight_string(cls, weight_str: str) -> str:
        """Normalize weight string for consistent keys."""
        # Convert to lowercase and remove extra spaces
        normalized = weight_str.lower().strip()
        
        # Standardize common variations
        replacements = {
            "kilograms": "kg",
            "kilogram": "kg",
            "pounds": "lb",
            "pound": "lb",
            "ounces": "oz",
            "ounce": "oz",
            "grams": "g",
            "gram": "g",
            " ": "_",  # Replace spaces with underscores
            ",": "",   # Remove commas
            ".": "_",  # Replace dots with underscores for key safety
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        # Remove any remaining special characters
        normalized = re.sub(r'[^a-z0-9_]', '', normalized)
        
        return normalized
    
    @classmethod
    def _normalize_prompt_variables(cls, variables: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize prompt variables for consistent hashing."""
        normalized = {}
        
        for key, value in variables.items():
            if isinstance(value, float):
                # Round floats to 4 decimal places
                normalized[key] = round(value, 4)
            elif isinstance(value, Decimal):
                # Convert Decimal to float with rounding
                normalized[key] = round(float(value), 4)
            elif isinstance(value, str):
                # Lowercase and strip strings
                normalized[key] = value.lower().strip()
            elif isinstance(value, (dict, list)):
                # Recursively normalize complex types
                normalized[key] = cls._normalize_complex_value(value)
            else:
                normalized[key] = value
        
        return normalized
    
    @classmethod
    def _normalize_complex_value(cls, value: Any) -> Any:
        """Recursively normalize complex values."""
        if isinstance(value, dict):
            return {k: cls._normalize_complex_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [cls._normalize_complex_value(item) for item in value]
        elif isinstance(value, float):
            return round(value, 4)
        elif isinstance(value, str):
            return value.lower().strip()
        else:
            return value
    
    @classmethod
    def _ensure_key_length(cls, key: str) -> str:
        """Ensure key doesn't exceed Redis length limits."""
        if len(key) <= cls.MAX_KEY_LENGTH:
            return key
        
        # If too long, hash the excess part
        prefix_length = cls.MAX_KEY_LENGTH - 32 - 1  # Leave room for hash + separator
        prefix = key[:prefix_length]
        
        # Hash the full key
        key_hash = hashlib.md5(key.encode()).hexdigest()
        
        return f"{prefix}_{key_hash}"
    
    @classmethod
    def validate_key(cls, key: str) -> bool:
        """
        Validate cache key format and safety.
        
        Args:
            key: Cache key to validate
            
        Returns:
            True if key is valid, False otherwise
        """
        # Check length
        if len(key) > cls.MAX_KEY_LENGTH:
            return False
        
        # Check for dangerous characters
        dangerous_chars = [" ", "\n", "\r", "\t"]
        if any(char in key for char in dangerous_chars):
            return False
        
        # Check for Redis command injection patterns
        redis_commands = ["FLUSHALL", "FLUSHDB", "EVAL", "SCRIPT"]
        key_upper = key.upper()
        if any(cmd in key_upper for cmd in redis_commands):
            return False
        
        return True