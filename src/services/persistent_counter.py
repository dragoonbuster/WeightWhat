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
        # Use a more permanent location with multiple fallbacks
        if storage_path:
            self.storage_path = storage_path
        else:
            # Try multiple locations in order of preference
            possible_paths = [
                Path("/var/lib/weightwhat/counter.json"),
                Path("/opt/WeightWhat/data/counter.json"),
                Path.home() / ".weightwhat" / "counter.json",
                Path("/tmp/sizecomparator_counter.json")
            ]
            
            # Find the first writable location
            self.storage_path = None
            for path in possible_paths:
                try:
                    # Ensure parent directory exists
                    path.parent.mkdir(parents=True, exist_ok=True)
                    # Test if we can write to this location
                    test_file = path.parent / ".write_test"
                    test_file.touch()
                    test_file.unlink()
                    self.storage_path = path
                    logger.info(f"Using counter storage path: {path}")
                    break
                except Exception as e:
                    logger.debug(f"Cannot use {path}: {e}")
            
            if not self.storage_path:
                # Final fallback
                self.storage_path = Path("/tmp/sizecomparator_counter.json")
                logger.warning(f"Using temporary storage path: {self.storage_path}")
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
                        logger.info(f"Counter from Redis: {value}")
                        return int(value)
                except Exception as e:
                    logger.warning(f"Redis get failed: {e}, falling back to file storage")
            
            # Fall back to file storage
            try:
                if self.storage_path.exists():
                    data = json.loads(self.storage_path.read_text())
                    count = data.get("count", 0)
                    logger.info(f"Counter from file {self.storage_path}: {count}")
                    return count
                else:
                    # Try to find and migrate from old locations
                    count = await self._migrate_from_old_locations()
                    if count > 0:
                        logger.info(f"Migrated counter value: {count}")
                        return count
                    logger.info(f"Counter file {self.storage_path} does not exist, returning 0")
            except Exception as e:
                logger.warning(f"File read failed from {self.storage_path}: {e}, returning 0")
            
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
                
                # Ensure directory exists
                self.storage_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Save to file
                import time
                data = {"count": new_value, "updated_at": time.time()}
                self.storage_path.write_text(json.dumps(data))
                logger.info(f"Counter incremented to {new_value} and saved to {self.storage_path}")
                
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
            import time
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {"count": value, "updated_at": time.time()}
            self.storage_path.write_text(json.dumps(data))
            logger.info(f"File backup updated with counter: {value}")
        except Exception as e:
            logger.warning(f"Failed to update file backup: {e}")


# Global instance
_counter_instance: Optional[PersistentCounter] = None


    async def _migrate_from_old_locations(self) -> int:
        """Try to find and migrate counter from old locations"""
        old_locations = [
            Path("/var/lib/weightwhat/counter.json"),
            Path("/opt/WeightWhat/data/counter.json"),
            Path.home() / ".weightwhat" / "counter.json",
            Path("/tmp/sizecomparator_counter.json")
        ]
        
        for old_path in old_locations:
            if old_path != self.storage_path and old_path.exists():
                try:
                    data = json.loads(old_path.read_text())
                    count = data.get("count", 0)
                    if count > 0:
                        # Migrate to new location
                        await self.set(count)
                        logger.info(f"Migrated counter from {old_path} to {self.storage_path}")
                        # Keep old file as backup but rename it
                        try:
                            old_path.rename(old_path.with_suffix('.json.backup'))
                        except:
                            pass
                        return count
                except Exception as e:
                    logger.debug(f"Could not read old counter from {old_path}: {e}")
        
        return 0


def get_persistent_counter(redis_client=None) -> PersistentCounter:
    """Get or create the global persistent counter instance"""
    global _counter_instance
    if _counter_instance is None:
        _counter_instance = PersistentCounter(redis_client=redis_client)
    return _counter_instance