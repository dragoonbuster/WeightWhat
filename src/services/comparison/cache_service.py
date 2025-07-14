"""
Simple Cache Service Implementation

Basic in-memory cache implementation for development and testing.
In production, this would be replaced with Redis or similar.
"""

import asyncio
import time
from typing import Any, Optional, Dict


class MemoryCache:
    """Simple in-memory cache with TTL support"""
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cleanup_task = None
        self._start_cleanup_task()
        
    def _start_cleanup_task(self):
        """Start background cleanup task"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_expired())
            
    async def _cleanup_expired(self):
        """Periodically clean up expired items"""
        while True:
            try:
                current_time = time.time()
                expired_keys = []
                
                for key, data in self._cache.items():
                    if data["expires_at"] <= current_time:
                        expired_keys.append(key)
                        
                for key in expired_keys:
                    del self._cache[key]
                    
                await asyncio.sleep(60)  # Cleanup every minute
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(60)  # Continue on error
                
    async def get(self, key: str) -> Optional[Any]:
        """Get item from cache"""
        if key not in self._cache:
            return None
            
        data = self._cache[key]
        if data["expires_at"] <= time.time():
            del self._cache[key]
            return None
            
        return data["value"]
        
    async def set(self, key: str, value: Any, ttl: int = 86400) -> None:
        """Set item in cache with TTL"""
        expires_at = time.time() + ttl
        self._cache[key] = {
            "value": value,
            "expires_at": expires_at
        }
        
    def close(self):
        """Close cache and cleanup"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            self._cleanup_task = None