"""
Rate Limiter for API Usage Control

Simple rate limiting to prevent abuse and control costs.
"""

import time
import logging
from collections import defaultdict, deque
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class RateLimitInfo:
    """Information about rate limit status."""
    allowed: bool
    remaining: int
    reset_time: datetime
    limit: int
    window_seconds: int


class RateLimiter:
    """Simple sliding window rate limiter."""
    
    def __init__(self, config: Dict[str, any]):
        self.config = config
        self.enabled = config.get('rate_limiting_enabled', True)
        self.per_minute_limit = config.get('rate_limit_per_minute', 60)
        self.per_hour_limit = config.get('rate_limit_per_hour', 1000)
        
        # Storage for request timestamps
        self.minute_requests: Dict[str, deque] = defaultdict(deque)
        self.hour_requests: Dict[str, deque] = defaultdict(deque)
        
        # Cleanup timestamps
        self.last_cleanup = time.time()
        
    def check_rate_limit(self, identifier: str) -> RateLimitInfo:
        """Check if request is within rate limits."""
        if not self.enabled:
            return RateLimitInfo(
                allowed=True,
                remaining=999,
                reset_time=datetime.now() + timedelta(minutes=1),
                limit=999,
                window_seconds=60
            )
        
        self._cleanup_old_requests()
        
        now = time.time()
        
        # Check minute limit
        minute_queue = self.minute_requests[identifier]
        minute_limit_info = self._check_window_limit(
            minute_queue, now, 60, self.per_minute_limit
        )
        
        if not minute_limit_info.allowed:
            return minute_limit_info
        
        # Check hour limit
        hour_queue = self.hour_requests[identifier]
        hour_limit_info = self._check_window_limit(
            hour_queue, now, 3600, self.per_hour_limit
        )
        
        if not hour_limit_info.allowed:
            return hour_limit_info
        
        # Both limits passed, record the request
        minute_queue.append(now)
        hour_queue.append(now)
        
        return RateLimitInfo(
            allowed=True,
            remaining=min(minute_limit_info.remaining, hour_limit_info.remaining),
            reset_time=min(minute_limit_info.reset_time, hour_limit_info.reset_time),
            limit=min(self.per_minute_limit, self.per_hour_limit),
            window_seconds=60
        )
    
    def _check_window_limit(
        self, 
        request_queue: deque, 
        now: float, 
        window_seconds: int, 
        limit: int
    ) -> RateLimitInfo:
        """Check rate limit for a specific time window."""
        # Remove old requests outside the window
        cutoff_time = now - window_seconds
        while request_queue and request_queue[0] < cutoff_time:
            request_queue.popleft()
        
        current_count = len(request_queue)
        
        if current_count >= limit:
            # Find the oldest request to determine reset time
            oldest_request = request_queue[0] if request_queue else now
            reset_time = datetime.fromtimestamp(oldest_request + window_seconds)
            
            return RateLimitInfo(
                allowed=False,
                remaining=0,
                reset_time=reset_time,
                limit=limit,
                window_seconds=window_seconds
            )
        
        return RateLimitInfo(
            allowed=True,
            remaining=limit - current_count,
            reset_time=datetime.fromtimestamp(now + window_seconds),
            limit=limit,
            window_seconds=window_seconds
        )
    
    def _cleanup_old_requests(self):
        """Clean up old request records to prevent memory leaks."""
        now = time.time()
        
        # Only cleanup every 5 minutes
        if now - self.last_cleanup < 300:
            return
            
        self.last_cleanup = now
        
        # Clean up minute requests (keep only last hour)
        hour_cutoff = now - 3600
        for identifier in list(self.minute_requests.keys()):
            queue = self.minute_requests[identifier]
            while queue and queue[0] < hour_cutoff:
                queue.popleft()
            
            # Remove empty queues
            if not queue:
                del self.minute_requests[identifier]
        
        # Clean up hour requests (keep only last 24 hours)
        day_cutoff = now - 86400
        for identifier in list(self.hour_requests.keys()):
            queue = self.hour_requests[identifier]
            while queue and queue[0] < day_cutoff:
                queue.popleft()
            
            # Remove empty queues
            if not queue:
                del self.hour_requests[identifier]
        
        logger.debug(f"Rate limiter cleanup: {len(self.minute_requests)} minute queues, {len(self.hour_requests)} hour queues")
    
    def get_status(self, identifier: str) -> Dict[str, any]:
        """Get current rate limit status for an identifier."""
        self._cleanup_old_requests()
        
        now = time.time()
        minute_queue = self.minute_requests[identifier]
        hour_queue = self.hour_requests[identifier]
        
        # Clean up old requests
        minute_cutoff = now - 60
        hour_cutoff = now - 3600
        
        minute_count = sum(1 for t in minute_queue if t >= minute_cutoff)
        hour_count = sum(1 for t in hour_queue if t >= hour_cutoff)
        
        return {
            'per_minute': {
                'current': minute_count,
                'limit': self.per_minute_limit,
                'remaining': max(0, self.per_minute_limit - minute_count)
            },
            'per_hour': {
                'current': hour_count,
                'limit': self.per_hour_limit,
                'remaining': max(0, self.per_hour_limit - hour_count)
            },
            'enabled': self.enabled
        }
    
    def reset_limits(self, identifier: str):
        """Reset rate limits for an identifier (admin function)."""
        if identifier in self.minute_requests:
            del self.minute_requests[identifier]
        if identifier in self.hour_requests:
            del self.hour_requests[identifier]
        
        logger.info(f"Rate limits reset for {identifier}")