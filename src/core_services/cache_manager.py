"""
Simplified cache manager for SizeComparator.
Handles in-memory caching and counter persistence.
"""

import json
import time
import os
from pathlib import Path
from typing import Optional, Dict, Any
from threading import Lock

class CacheManager:
    """Simple in-memory cache with file-based counter persistence."""
    
    def __init__(self):
        # In-memory cache
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()
        
        # Counter persistence
        # Use project data directory for counter
        self._counter_file = Path(__file__).parent.parent.parent / 'data' / 'counter.json'
        self._counter_file.parent.mkdir(exist_ok=True)
        self._counter_value = self._load_counter()
    
    # Cache operations
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                # Check if expired
                if entry['expires'] > time.time():
                    return entry['value']
                else:
                    del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: int = 3600):
        """Set value in cache with TTL in seconds."""
        with self._lock:
            self._cache[key] = {
                'value': value,
                'expires': time.time() + ttl
            }
    
    def delete(self, key: str):
        """Delete key from cache."""
        with self._lock:
            self._cache.pop(key, None)
    
    def clear(self):
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
    
    # Counter operations
    def get_counter(self) -> int:
        """Get current counter value."""
        return self._counter_value
    
    def increment_counter(self) -> int:
        """Increment counter and persist."""
        with self._lock:
            self._counter_value += 1
            self._save_counter()
            return self._counter_value
    
    def _load_counter(self) -> int:
        """Load counter from file."""
        try:
            if self._counter_file.exists():
                with open(self._counter_file, 'r') as f:
                    data = json.load(f)
                    return data.get('count', 0)
        except:
            pass
        return 0
    
    def _save_counter(self):
        """Save counter to file."""
        try:
            with open(self._counter_file, 'w') as f:
                json.dump({
                    'count': self._counter_value,
                    'updated_at': time.time()
                }, f)
        except Exception as e:
            # Log but don't fail
            print(f"Failed to save counter: {e}")
    
    def build_cache_key(self, weight_kg: float, style: str = 'default') -> str:
        """Build cache key for comparison."""
        # Round weight for cache efficiency
        if weight_kg < 0.1:
            rounded = round(weight_kg, 4)
        elif weight_kg < 10:
            rounded = round(weight_kg, 2)
        elif weight_kg < 1000:
            rounded = round(weight_kg, 1)
        else:
            rounded = round(weight_kg, 0)
        
        return f"comparison:{rounded}:{style}"