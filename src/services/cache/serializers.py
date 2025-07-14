"""
Pydantic serialization for cache values

This module provides efficient serialization and deserialization of Pydantic models
for cache storage, with support for compression and type-safe conversion.
"""

import json
import zlib
import logging
from typing import Type, TypeVar, Optional, Any, Dict
from pydantic import BaseModel
from datetime import datetime
from decimal import Decimal
from uuid import UUID

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class CacheSerializer:
    """Handles serialization/deserialization with compression."""
    
    COMPRESSION_THRESHOLD = 1024  # Compress if larger than 1KB
    VERSION = "v1"
    
    @staticmethod
    def serialize(obj: BaseModel) -> bytes:
        """
        Serialize Pydantic model to bytes with optional compression.
        
        Args:
            obj: Pydantic model instance to serialize
            
        Returns:
            Serialized bytes with format prefix
        """
        try:
            # Convert to dictionary using Pydantic's model_dump
            data = obj.model_dump()
            
            # Create serialization envelope with metadata
            envelope = {
                "version": CacheSerializer.VERSION,
                "model_type": obj.__class__.__name__,
                "model_module": obj.__class__.__module__,
                "data": data,
                "serialized_at": datetime.utcnow().isoformat()
            }
            
            # Serialize to JSON with custom encoder
            json_str = json.dumps(envelope, default=CacheSerializer._json_encoder)
            json_bytes = json_str.encode('utf-8')
            
            # Compress if larger than threshold
            if len(json_bytes) > CacheSerializer.COMPRESSION_THRESHOLD:
                compressed = zlib.compress(json_bytes, level=6)
                # Add compression marker
                return b'Z:' + compressed
            
            # Add JSON marker
            return b'J:' + json_bytes
            
        except Exception as e:
            logger.error(f"Failed to serialize {obj.__class__.__name__}: {e}")
            raise ValueError(f"Serialization failed: {e}")
    
    @staticmethod
    def deserialize(data: bytes, model_class: Type[T]) -> T:
        """
        Deserialize bytes to Pydantic model.
        
        Args:
            data: Serialized bytes from cache
            model_class: Pydantic model class to deserialize to
            
        Returns:
            Deserialized Pydantic model instance
        """
        try:
            # Check format prefix
            if data.startswith(b'Z:'):
                # Decompress
                json_bytes = zlib.decompress(data[2:])
            elif data.startswith(b'J:'):
                # Remove JSON marker
                json_bytes = data[2:]
            else:
                # Legacy format - assume raw JSON
                json_bytes = data
            
            # Parse JSON
            envelope = json.loads(json_bytes.decode('utf-8'))
            
            # Handle both envelope and direct data formats
            if isinstance(envelope, dict) and "version" in envelope:
                # New envelope format
                model_data = envelope["data"]
                stored_type = envelope.get("model_type")
                
                # Validate model type matches (optional warning)
                if stored_type and stored_type != model_class.__name__:
                    logger.warning(
                        f"Model type mismatch: stored {stored_type}, "
                        f"requested {model_class.__name__}"
                    )
            else:
                # Legacy format or direct data
                model_data = envelope
            
            # Validate and create model instance
            return model_class.model_validate(model_data)
            
        except zlib.error as e:
            logger.error(f"Decompression failed: {e}")
            raise ValueError(f"Invalid compressed data: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            raise ValueError(f"Invalid JSON data: {e}")
        except Exception as e:
            logger.error(f"Failed to deserialize to {model_class.__name__}: {e}")
            raise ValueError(f"Deserialization failed: {e}")
    
    @staticmethod
    def serialize_simple(value: Any) -> bytes:
        """
        Serialize simple Python objects (non-Pydantic).
        
        Args:
            value: Python object to serialize
            
        Returns:
            Serialized bytes
        """
        try:
            json_str = json.dumps(value, default=CacheSerializer._json_encoder)
            return json_str.encode('utf-8')
        except Exception as e:
            logger.error(f"Failed to serialize simple value: {e}")
            raise ValueError(f"Simple serialization failed: {e}")
    
    @staticmethod
    def deserialize_simple(data: bytes, target_type: Optional[Type] = None) -> Any:
        """
        Deserialize simple Python objects.
        
        Args:
            data: Serialized bytes
            target_type: Optional type hint for conversion
            
        Returns:
            Deserialized Python object
        """
        try:
            json_str = data.decode('utf-8')
            value = json.loads(json_str)
            
            # Optional type conversion
            if target_type and value is not None:
                if target_type == Decimal and isinstance(value, (int, float, str)):
                    return Decimal(str(value))
                elif target_type == datetime and isinstance(value, str):
                    return datetime.fromisoformat(value)
                elif target_type == UUID and isinstance(value, str):
                    return UUID(value)
            
            return value
            
        except Exception as e:
            logger.error(f"Failed to deserialize simple value: {e}")
            raise ValueError(f"Simple deserialization failed: {e}")
    
    @staticmethod
    def _json_encoder(obj: Any) -> Any:
        """Custom JSON encoder for special types."""
        if isinstance(obj, Decimal):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, UUID):
            return str(obj)
        elif hasattr(obj, 'model_dump'):
            # Handle nested Pydantic models
            return obj.model_dump()
        elif hasattr(obj, '__dict__'):
            # Handle simple objects with __dict__
            return obj.__dict__
        else:
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    @staticmethod
    def get_compression_stats(data: bytes) -> Dict[str, Any]:
        """
        Get compression statistics for serialized data.
        
        Args:
            data: Serialized bytes
            
        Returns:
            Dictionary with compression info
        """
        is_compressed = data.startswith(b'Z:')
        
        if is_compressed:
            compressed_size = len(data) - 2  # Subtract prefix
            try:
                uncompressed = zlib.decompress(data[2:])
                original_size = len(uncompressed)
                compression_ratio = compressed_size / original_size
            except:
                original_size = 0
                compression_ratio = 0
        else:
            compressed_size = 0
            original_size = len(data) - 2 if data.startswith(b'J:') else len(data)
            compression_ratio = 1.0
        
        return {
            "is_compressed": is_compressed,
            "compressed_size": compressed_size,
            "original_size": original_size,
            "compression_ratio": compression_ratio,
            "savings_bytes": original_size - compressed_size if is_compressed else 0,
            "savings_percent": (1 - compression_ratio) * 100 if is_compressed else 0
        }


class ModelRegistry:
    """Registry for dynamically resolving model classes during deserialization."""
    
    _registry: Dict[str, Type[BaseModel]] = {}
    
    @classmethod
    def register(cls, model_class: Type[BaseModel]) -> None:
        """
        Register a model class for dynamic resolution.
        
        Args:
            model_class: Pydantic model class to register
        """
        key = f"{model_class.__module__}.{model_class.__name__}"
        cls._registry[key] = model_class
        logger.debug(f"Registered model class: {key}")
    
    @classmethod
    def get(cls, module: str, name: str) -> Optional[Type[BaseModel]]:
        """
        Get registered model class.
        
        Args:
            module: Module name
            name: Class name
            
        Returns:
            Model class if found, None otherwise
        """
        key = f"{module}.{name}"
        return cls._registry.get(key)
    
    @classmethod
    def auto_register_from_module(cls, module_name: str) -> None:
        """
        Automatically register all Pydantic models from a module.
        
        Args:
            module_name: Name of module to scan
        """
        try:
            import importlib
            module = importlib.import_module(module_name)
            
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BaseModel) and 
                    attr is not BaseModel):
                    cls.register(attr)
                    
        except Exception as e:
            logger.error(f"Failed to auto-register from {module_name}: {e}")


# Auto-register common model classes
try:
    # Register models from the application
    ModelRegistry.auto_register_from_module("src.models.weight")
    ModelRegistry.auto_register_from_module("src.models.responses")
    ModelRegistry.auto_register_from_module("src.models.providers")
    ModelRegistry.auto_register_from_module("src.models.config")
    ModelRegistry.auto_register_from_module("src.models.requests")
except Exception as e:
    logger.warning(f"Could not auto-register all models: {e}")


class TypeSafeSerializer:
    """Type-safe wrapper around CacheSerializer for specific model types."""
    
    def __init__(self, model_class: Type[T]):
        """
        Initialize with specific model class.
        
        Args:
            model_class: Pydantic model class this serializer handles
        """
        self.model_class = model_class
        self.serializer = CacheSerializer()
    
    async def serialize(self, obj: T) -> bytes:
        """Serialize instance of the configured model type."""
        if not isinstance(obj, self.model_class):
            raise TypeError(f"Expected {self.model_class.__name__}, got {type(obj).__name__}")
        return self.serializer.serialize(obj)
    
    async def deserialize(self, data: bytes) -> T:
        """Deserialize to instance of the configured model type."""
        return self.serializer.deserialize(data, self.model_class)


# Convenience functions for common model types
def create_weight_serializer():
    """Create serializer for ProcessedWeight models."""
    from src.models.weight import ProcessedWeight
    return TypeSafeSerializer(ProcessedWeight)

def create_response_serializer():
    """Create serializer for AIProviderResponse models."""
    from src.models.providers import AIProviderResponse
    return TypeSafeSerializer(AIProviderResponse)

def create_config_serializer():
    """Create serializer for configuration models."""
    from src.models.config import CachedConfig
    return TypeSafeSerializer(CachedConfig)