"""
In-memory cache implementation for development

This module provides a simple in-memory cache for development environments
where Redis is not available or needed.
"""

import asyncio
import fnmatch
import time
from typing import Optional, List, Dict, Any, Type
from pydantic import BaseModel

from .base import CacheService

T = Any


class MemoryCache(CacheService[T]):
    """Simple in-memory cache implementation for development."""
    
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, Any] = {}
        self._ttls: Dict[str, float] = {}
        self.max_size = max_size
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "deletes": 0
        }
    
    async def get(self, key: str, model_class: Optional[Type[BaseModel]] = None) -> Optional[T]:
        """Get value from memory cache."""
        # Check if key exists and hasn't expired
        if key in self._cache:
            if key in self._ttls:
                if time.time() > self._ttls[key]:
                    # Expired
                    del self._cache[key]
                    del self._ttls[key]
                    self._stats["misses"] += 1
                    return None
            
            self._stats["hits"] += 1
            return self._cache[key]
        
        self._stats["misses"] += 1
        return None
    
    async def set(self, key: str, value: T, ttl: Optional[int] = None) -> bool:
        """Set value in memory cache."""
        # Simple LRU eviction if cache is full
        if len(self._cache) >= self.max_size and key not in self._cache:
            # Remove oldest entry
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            if oldest_key in self._ttls:
                del self._ttls[oldest_key]
        
        self._cache[key] = value
        if ttl:
            self._ttls[key] = time.time() + ttl
        
        self._stats["sets"] += 1
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete from memory cache."""
        if key in self._cache:
            del self._cache[key]
            if key in self._ttls:
                del self._ttls[key]
            self._stats["deletes"] += 1
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in memory."""
        return key in self._cache
    
    async def flush(self, pattern: Optional[str] = None) -> int:
        """Flush memory cache."""
        if pattern is None:
            count = len(self._cache)
            self._cache.clear()
            self._ttls.clear()
            return count
        else:
            # Simple pattern matching for development
            keys_to_delete = [k for k in self._cache if fnmatch.fnmatch(k, pattern)]
            for key in keys_to_delete:
                await self.delete(key)
            return len(keys_to_delete)
    
    async def get_ttl(self, key: str) -> Optional[int]:
        """Get TTL from memory cache."""
        if key in self._ttls:
            remaining = self._ttls[key] - time.time()
            return max(0, int(remaining))
        return None
    
    async def extend_ttl(self, key: str, ttl: int) -> bool:
        """Extend TTL in memory cache."""
        if key in self._cache:
            self._ttls[key] = time.time() + ttl
            return True
        return False
    
    async def multi_get(
        self, 
        keys: List[str],
        model_class: Optional[Type[BaseModel]] = None
    ) -> Dict[str, Optional[T]]:
        """Get multiple keys from memory."""
        result = {}
        for key in keys:
            result[key] = await self.get(key, model_class)
        return result
    
    async def multi_set(self, items: Dict[str, T], ttl: Optional[int] = None) -> bool:
        """Set multiple keys in memory."""
        for key, value in items.items():
            await self.set(key, value, ttl)
        return True
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment value in memory."""
        current = await self.get(key)
        if current is None:
            new_value = amount
        else:
            new_value = int(current) + amount
        await self.set(key, new_value)
        return new_value
    
    async def set_if_not_exists(self, key: str, value: T, ttl: Optional[int] = None) -> bool:
        """Set if not exists in memory."""
        if key not in self._cache:
            return await self.set(key, value, ttl)
        return False
    
    async def health_check(self) -> bool:
        """Memory cache is always healthy."""
        return True
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory cache stats."""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_requests) if total_requests > 0 else 0.0
        
        return {
            "type": "memory",
            "keys": len(self._cache),
            "max_size": self.max_size,
            "hit_rate": hit_rate,
            "stats": self._stats,
            "memory_usage": "N/A"
        }