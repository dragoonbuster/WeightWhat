"""
Abstract cache interface for SizeComparator

This module defines the base cache service interface that all cache implementations
must follow. It provides type-safe methods for cache operations and integrates
with the environment manager for configuration.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, TypeVar, Generic, Type
from datetime import timedelta
import asyncio
from pydantic import BaseModel

from src.core.environment import EnvironmentManager

T = TypeVar('T')


class CacheError(Exception):
    """Base exception for cache operations"""
    pass


class CacheConnectionError(CacheError):
    """Cache connection error"""
    pass


class CacheService(ABC, Generic[T]):
    """Abstract base class for cache implementations."""
    
    @abstractmethod
    async def get(self, key: str, model_class: Optional[Type[BaseModel]] = None) -> Optional[T]:
        """
        Retrieve value from cache.
        
        Args:
            key: Cache key
            model_class: Optional Pydantic model class for deserialization
            
        Returns:
            Cached value or None if not found
        """
        pass
    
    @abstractmethod
    async def set(
        self, 
        key: str, 
        value: T, 
        ttl: Optional[int] = None
    ) -> bool:
        """
        Store value in cache with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable or Pydantic model)
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Remove value from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False if key didn't exist
        """
        pass
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def flush(self, pattern: Optional[str] = None) -> int:
        """
        Flush cache keys matching pattern.
        
        Args:
            pattern: Optional glob pattern (e.g., "user")
            
        Returns:
            Number of keys deleted
        """
        pass
    
    @abstractmethod
    async def get_ttl(self, key: str) -> Optional[int]:
        """
        Get remaining TTL for key.
        
        Args:
            key: Cache key
            
        Returns:
            Remaining TTL in seconds or None if key doesn't exist
        """
        pass
    
    @abstractmethod
    async def extend_ttl(self, key: str, ttl: int) -> bool:
        """
        Extend TTL for existing key.
        
        Args:
            key: Cache key
            ttl: New TTL in seconds
            
        Returns:
            True if TTL was extended, False if key doesn't exist
        """
        pass
    
    @abstractmethod
    async def multi_get(
        self, 
        keys: List[str],
        model_class: Optional[Type[BaseModel]] = None
    ) -> Dict[str, Optional[T]]:
        """
        Get multiple keys efficiently.
        
        Args:
            keys: List of cache keys
            model_class: Optional Pydantic model class for deserialization
            
        Returns:
            Dictionary mapping keys to values (None if not found)
        """
        pass
    
    @abstractmethod
    async def multi_set(
        self, 
        items: Dict[str, T], 
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set multiple keys efficiently.
        
        Args:
            items: Dictionary of key-value pairs
            ttl: Optional TTL for all keys
            
        Returns:
            True if all keys were set successfully
        """
        pass
    
    @abstractmethod
    async def increment(
        self, 
        key: str, 
        amount: int = 1
    ) -> int:
        """
        Atomic increment operation.
        
        Args:
            key: Cache key
            amount: Amount to increment by
            
        Returns:
            New value after increment
        """
        pass
    
    @abstractmethod
    async def set_if_not_exists(
        self, 
        key: str, 
        value: T, 
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value only if key doesn't exist.
        
        Args:
            key: Cache key
            value: Value to set
            ttl: Optional TTL
            
        Returns:
            True if value was set, False if key already existed
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check cache health.
        
        Returns:
            True if cache is healthy, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary of cache statistics
        """
        pass
    
    @classmethod
    def from_env(cls, env_manager: Optional[EnvironmentManager] = None) -> 'CacheService':
        """
        Create cache service from environment configuration.
        
        Args:
            env_manager: Optional environment manager instance
            
        Returns:
            Configured cache service instance
        """
        if env_manager is None:
            from src.core.environment import create_environment_manager
            env_manager = create_environment_manager()
        
        # Get Redis configuration from environment
        # Default to Redis being enabled
        redis_host = env_manager.get_variable("SIZECOMPARATOR_REDIS_HOST", "localhost")
        
        # Only use Redis if host is configured or is localhost (dev)
        if redis_host:
            from .redis_cache import RedisCache, RedisConfig
            
            config = RedisConfig(
                host=redis_host,
                port=env_manager.get_variable("SIZECOMPARATOR_REDIS_PORT", 6379),
                password=env_manager.get_variable("SIZECOMPARATOR_REDIS_PASSWORD", mask_sensitive=False),
                db=env_manager.get_variable("SIZECOMPARATOR_REDIS_DB", 0),
                tls_enabled=env_manager.get_variable("SIZECOMPARATOR_REDIS_TLS", False),
                max_connections=50,  # Default values since these aren't in env registry
                socket_timeout=5.0,
                decode_responses=False,  # We handle encoding/decoding ourselves
                retry_on_timeout=True,
                retry_on_error=[ConnectionError, TimeoutError],
                health_check_interval=30,
            )
            
            return RedisCache(config)
        else:
            # Fallback to in-memory cache for development
            from .memory_cache import MemoryCache
            return MemoryCache()