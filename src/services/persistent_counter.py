"""
Persistent Counter Service

Provides a global counter that persists across server restarts.
Uses Redis if available, falls back to file-based storage.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PersistentCounter:
    """Manages a persistent global counter for weight comparisons"""
    
    def __init__(self, redis_client=None, storage_path: Optional[Path] = None):
        """
        Initialize the persistent counter.
        
        Args:
            redis_client: Optional Redis client for distributed storage
            storage_path: Path to local file storage (defaults to /tmp/sizecomparator_counter.json)
        """
        self.redis_client = redis_client
        self.storage_path = storage_path or Path("/tmp/sizecomparator_counter.json")
        self.redis_key = "sizecomparator:global_weight_comparisons_count"
        self._local_cache = None
        self._lock = asyncio.Lock()
    
    async def get(self) -> int:
        """Get the current counter value"""
        async with self._lock:
            # Try Redis first
            if self.redis_client:
                try:
                    value = await self.redis_client.get(self.redis_key)
                    if value is not None:
                        return int(value)
                except Exception as e:
                    logger.warning(f"Redis get failed: {e}, falling back to file storage")
            
            # Fall back to file storage
            try:
                if self.storage_path.exists():
                    data = json.loads(self.storage_path.read_text())
                    return data.get("count", 0)
            except Exception as e:
                logger.warning(f"File read failed: {e}, returning 0")
            
            return 0
    
    async def increment(self) -> int:
        """Increment the counter and return the new value"""
        async with self._lock:
            # Try Redis first
            if self.redis_client:
                try:
                    new_value = await self.redis_client.incr(self.redis_key)
                    # Also update file backup
                    self._update_file_backup(new_value)
                    return new_value
                except Exception as e:
                    logger.warning(f"Redis increment failed: {e}, falling back to file storage")
            
            # Fall back to file storage
            try:
                current = await self.get()
                new_value = current + 1
                
                # Save to file
                data = {"count": new_value, "updated_at": str(asyncio.get_event_loop().time())}
                self.storage_path.write_text(json.dumps(data))
                
                # Try to sync to Redis if available
                if self.redis_client:
                    try:
                        await self.redis_client.set(self.redis_key, str(new_value))
                    except Exception:
                        pass  # Silent fail, file is primary
                
                return new_value
            except Exception as e:
                logger.error(f"Failed to increment counter: {e}")
                return 0
    
    async def set(self, value: int) -> None:
        """Set the counter to a specific value (admin use only)"""
        async with self._lock:
            # Update both Redis and file
            if self.redis_client:
                try:
                    await self.redis_client.set(self.redis_key, str(value))
                except Exception as e:
                    logger.warning(f"Redis set failed: {e}")
            
            # Always update file
            data = {"count": value, "updated_at": str(asyncio.get_event_loop().time())}
            self.storage_path.write_text(json.dumps(data))
    
    def _update_file_backup(self, value: int) -> None:
        """Update file backup without async (for use in Redis path)"""
        try:
            data = {"count": value, "updated_at": str(asyncio.get_event_loop().time())}
            self.storage_path.write_text(json.dumps(data))
        except Exception as e:
            logger.warning(f"Failed to update file backup: {e}")


# Global instance
_counter_instance: Optional[PersistentCounter] = None


def get_persistent_counter(redis_client=None) -> PersistentCounter:
    """Get or create the global persistent counter instance"""
    global _counter_instance
    if _counter_instance is None:
        _counter_instance = PersistentCounter(redis_client=redis_client)
    return _counter_instance