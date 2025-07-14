"""
Redis implementation of cache service

This module provides a production-ready Redis cache implementation with:
- Connection pooling and health checks
- Circuit breaker protection
- Batch operations and pipelining
- Comprehensive metrics collection
- Multiple deployment mode support (standalone, sentinel, cluster)
"""

import asyncio
import logging
from typing import Optional, List, Dict, Any, Type, Union
from datetime import datetime
import redis.asyncio as redis
from redis.asyncio.sentinel import Sentinel
from redis.exceptions import RedisError, ConnectionError, TimeoutError
from pydantic import BaseModel, Field
from collections import defaultdict
import time

from .base import CacheService, CacheError, CacheConnectionError
from .serializers import CacheSerializer
from .key_builder import CacheKeyBuilder
# Simple circuit breaker implementation for cache
class CircuitBreaker:
    """Simple circuit breaker for cache operations."""
    
    def __init__(self, failure_threshold=5, recovery_timeout=60, expected_exception=Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
    
    async def call(self, func, *args, **kwargs):
        """Execute function through circuit breaker."""
        import time
        
        # Check if we should transition from open to half-open
        if (self.state == "open" and self.last_failure_time and 
            time.time() - self.last_failure_time > self.recovery_timeout):
            self.state = "half_open"
            logger.info("Circuit breaker transitioning to half-open")
        
        # Reject calls if circuit is open
        if self.state == "open":
            raise CacheConnectionError("Circuit breaker is open")
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            # Success - reset failure count and close circuit
            if self.state == "half_open":
                self.state = "closed"
                logger.info("Circuit breaker closed after successful call")
            self.failure_count = 0
            return result
            
        except self.expected_exception as e:
            # Handle expected failures
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
            
            raise

logger = logging.getLogger(__name__)

T = Union[str, bytes, int, float, BaseModel, Dict[str, Any], List[Any]]


class RedisConfig(BaseModel):
    """Redis configuration model."""
    mode: str = Field(default="standalone", description="Redis mode: standalone, sentinel, or cluster")
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    password: Optional[str] = Field(default=None, description="Redis password")
    db: int = Field(default=0, description="Redis database number")
    
    # Sentinel configuration
    sentinels: Optional[List[tuple[str, int]]] = Field(default=None, description="Sentinel nodes")
    master_name: Optional[str] = Field(default=None, description="Sentinel master name")
    
    # Cluster configuration
    nodes: Optional[List[tuple[str, int]]] = Field(default=None, description="Cluster nodes")
    
    # Connection settings
    max_connections: int = Field(default=50, description="Maximum connections in pool")
    socket_timeout: float = Field(default=5.0, description="Socket timeout in seconds")
    socket_connect_timeout: float = Field(default=5.0, description="Socket connect timeout")
    socket_keepalive: bool = Field(default=True, description="Enable TCP keepalive")
    socket_keepalive_options: Optional[Dict[int, int]] = Field(default=None, description="Keepalive options")
    
    # TLS settings
    tls_enabled: bool = Field(default=False, description="Enable TLS")
    ssl_certfile: Optional[str] = Field(default=None, description="SSL certificate file")
    ssl_keyfile: Optional[str] = Field(default=None, description="SSL key file")
    ssl_ca_certs: Optional[str] = Field(default=None, description="SSL CA certificates")
    
    # Behavior settings
    decode_responses: bool = Field(default=False, description="Decode responses to strings")
    retry_on_timeout: bool = Field(default=True, description="Retry on timeout")
    retry_on_error: Optional[List[type]] = Field(default=None, description="Errors to retry on")
    health_check_interval: int = Field(default=30, description="Health check interval in seconds")
    
    # Memory management
    max_memory: Optional[str] = Field(default=None, description="Max memory limit (e.g., '1GB')")
    eviction_policy: str = Field(default="allkeys-lru", description="Eviction policy")


class CacheMetrics:
    """Track cache performance metrics."""
    
    def __init__(self):
        self.operations = defaultdict(lambda: {
            "count": 0,
            "total_time": 0.0,
            "errors": 0
        })
        self.hit_miss = defaultdict(lambda: {
            "hits": 0,
            "misses": 0
        })
        self._start_time = time.time()
    
    def record_operation_time(self, operation: str, duration: float) -> None:
        """Record operation performance."""
        self.operations[operation]["count"] += 1
        self.operations[operation]["total_time"] += duration
    
    def record_error(self, operation: str, error: str) -> None:
        """Record operation error."""
        self.operations[operation]["errors"] += 1
        logger.error(f"Cache operation error - {operation}: {error}")
    
    def record_hit(self, key_prefix: str) -> None:
        """Record cache hit."""
        prefix = key_prefix.split(":")[0] if ":" in key_prefix else "default"
        self.hit_miss[prefix]["hits"] += 1
    
    def record_miss(self, key_prefix: str) -> None:
        """Record cache miss."""
        prefix = key_prefix.split(":")[0] if ":" in key_prefix else "default"
        self.hit_miss[prefix]["misses"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        total_ops = sum(op["count"] for op in self.operations.values())
        total_errors = sum(op["errors"] for op in self.operations.values())
        
        stats = {
            "uptime_seconds": int(time.time() - self._start_time),
            "total_operations": total_ops,
            "total_errors": total_errors,
            "error_rate": total_errors / total_ops if total_ops > 0 else 0.0,
            "operations": {},
            "hit_rates": {}
        }
        
        # Operation statistics
        for op_name, op_stats in self.operations.items():
            if op_stats["count"] > 0:
                stats["operations"][op_name] = {
                    "count": op_stats["count"],
                    "avg_time_ms": (op_stats["total_time"] / op_stats["count"]) * 1000,
                    "error_rate": op_stats["errors"] / op_stats["count"]
                }
        
        # Hit rate statistics
        for prefix, hit_stats in self.hit_miss.items():
            total = hit_stats["hits"] + hit_stats["misses"]
            if total > 0:
                stats["hit_rates"][prefix] = {
                    "hit_rate": hit_stats["hits"] / total,
                    "total_requests": total,
                    "hits": hit_stats["hits"],
                    "misses": hit_stats["misses"]
                }
        
        return stats


class RedisConnectionManager:
    """Manages Redis connections with pooling and health checks."""
    
    def __init__(self, config: RedisConfig):
        self.config = config
        self.client: Optional[redis.Redis] = None
        self.pool: Optional[redis.ConnectionPool] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._last_health_check: Optional[datetime] = None
        self._is_healthy = True
    
    async def initialize(self) -> None:
        """Initialize Redis connection based on topology."""
        try:
            if self.config.mode == "standalone":
                await self._init_standalone()
            elif self.config.mode == "sentinel":
                await self._init_sentinel()
            elif self.config.mode == "cluster":
                await self._init_cluster()
            else:
                raise ValueError(f"Unknown Redis mode: {self.config.mode}")
            
            # Test connection
            await self.client.ping()
            self._is_healthy = True
            
            # Start health check task
            self._health_check_task = asyncio.create_task(self._health_check_loop())
            
        except Exception as e:
            self._is_healthy = False
            raise CacheConnectionError(f"Failed to initialize Redis connection: {e}")
    
    async def _init_standalone(self) -> None:
        """Initialize standalone Redis connection."""
        pool_kwargs = self._get_pool_kwargs()
        self.pool = redis.ConnectionPool(**pool_kwargs)
        self.client = redis.Redis(connection_pool=self.pool)
    
    async def _init_sentinel(self) -> None:
        """Initialize Redis Sentinel connection."""
        if not self.config.sentinels or not self.config.master_name:
            raise ValueError("Sentinels and master_name required for sentinel mode")
        
        sentinel = Sentinel(
            self.config.sentinels,
            socket_timeout=self.config.socket_timeout,
            password=self.config.password,
            socket_keepalive=self.config.socket_keepalive
        )
        
        self.client = sentinel.master_for(
            self.config.master_name,
            socket_timeout=self.config.socket_timeout,
            connection_pool_kwargs=self._get_pool_kwargs()
        )
    
    async def _init_cluster(self) -> None:
        """Initialize Redis Cluster connection."""
        # Note: redis-py doesn't have full async cluster support yet
        # This is a placeholder for future implementation
        raise NotImplementedError("Redis Cluster support coming soon")
    
    def _get_pool_kwargs(self) -> Dict[str, Any]:
        """Get connection pool configuration."""
        kwargs = {
            "host": self.config.host,
            "port": self.config.port,
            "db": self.config.db,
            "password": self.config.password,
            "max_connections": self.config.max_connections,
            "socket_timeout": self.config.socket_timeout,
            "socket_connect_timeout": self.config.socket_connect_timeout,
            "socket_keepalive": self.config.socket_keepalive,
            "retry_on_timeout": self.config.retry_on_timeout,
        }
        
        # Add keepalive options
        if self.config.socket_keepalive_options:
            kwargs["socket_keepalive_options"] = self.config.socket_keepalive_options
        
        # Add TLS settings
        if self.config.tls_enabled:
            kwargs["ssl"] = True
            if self.config.ssl_certfile:
                kwargs["ssl_certfile"] = self.config.ssl_certfile
            if self.config.ssl_keyfile:
                kwargs["ssl_keyfile"] = self.config.ssl_keyfile
            if self.config.ssl_ca_certs:
                kwargs["ssl_ca_certs"] = self.config.ssl_ca_certs
        
        return kwargs
    
    async def _health_check_loop(self) -> None:
        """Continuous health checking with automatic reconnection."""
        while True:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                await self.health_check()
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                self._is_healthy = False
                # Try to reconnect
                await self._reconnect()
    
    async def health_check(self) -> bool:
        """Perform health check."""
        try:
            start_time = time.time()
            await self.client.ping()
            response_time = (time.time() - start_time) * 1000
            
            self._last_health_check = datetime.utcnow()
            self._is_healthy = True
            
            if response_time > 100:  # Warn if slow
                logger.warning(f"Redis health check slow: {response_time:.2f}ms")
            
            return True
            
        except Exception as e:
            self._is_healthy = False
            logger.error(f"Redis health check failed: {e}")
            return False
    
    async def _reconnect(self) -> None:
        """Attempt to reconnect with exponential backoff."""
        reconnect_attempts = 3
        reconnect_delay = 1.0
        
        for attempt in range(reconnect_attempts):
            try:
                delay = reconnect_delay * (2 ** attempt)
                logger.info(f"Attempting Redis reconnection (attempt {attempt + 1}/{reconnect_attempts})")
                await asyncio.sleep(delay)
                
                # Reinitialize connection
                await self.initialize()
                logger.info("Redis reconnection successful")
                return
                
            except Exception as e:
                logger.error(f"Reconnection attempt {attempt + 1} failed: {e}")
        
        logger.critical("Failed to reconnect to Redis after all attempts")
    
    async def close(self) -> None:
        """Close Redis connection and cleanup."""
        if self._health_check_task:
            self._health_check_task.cancel()
        
        if self.client:
            await self.client.close()
        
        if self.pool:
            await self.pool.disconnect()


class RedisCache(CacheService[T]):
    """Redis implementation of cache service with full feature support."""
    
    def __init__(self, config: RedisConfig):
        self.config = config
        self.connection_manager = RedisConnectionManager(config)
        self.serializer = CacheSerializer()
        self.key_builder = CacheKeyBuilder()
        self.metrics = CacheMetrics()
        
        # Circuit breaker for fault tolerance
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=RedisError
        )
        
        # Default TTLs by key prefix (in seconds)
        self._default_ttls = {
            "ai_response": 86400,    # 24 hours
            "config": 300,           # 5 minutes
            "weight": 3600,          # 1 hour
            "temp": 60,              # 1 minute
        }
        
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize Redis connection and monitoring."""
        if self._initialized:
            return
        
        await self.connection_manager.initialize()
        self._initialized = True
        logger.info(f"Redis cache initialized in {self.config.mode} mode")
    
    async def _ensure_initialized(self) -> None:
        """Ensure cache is initialized before operations."""
        if not self._initialized:
            await self.initialize()
    
    async def get(self, key: str, model_class: Optional[Type[BaseModel]] = None) -> Optional[T]:
        """Retrieve value with circuit breaker protection."""
        await self._ensure_initialized()
        return await self._circuit_breaker.call(self._get_impl, key, model_class)
    
    async def _get_impl(self, key: str, model_class: Optional[Type[BaseModel]] = None) -> Optional[T]:
        """Internal get implementation."""
        start_time = time.time()
        
        try:
            data = await self.connection_manager.client.get(key)
            
            if data is None:
                self.metrics.record_miss(key)
                return None
            
            self.metrics.record_hit(key)
            
            # Deserialize if model class provided
            if model_class and isinstance(data, bytes):
                return self.serializer.deserialize(data, model_class)
            
            return data
            
        except Exception as e:
            self.metrics.record_error("get", str(e))
            raise CacheError(f"Failed to get key {key}: {e}")
        finally:
            duration = time.time() - start_time
            self.metrics.record_operation_time("get", duration)
    
    async def set(self, key: str, value: T, ttl: Optional[int] = None) -> bool:
        """Store value with automatic TTL based on key type."""
        await self._ensure_initialized()
        return await self._circuit_breaker.call(self._set_impl, key, value, ttl)
    
    async def _set_impl(self, key: str, value: T, ttl: Optional[int] = None) -> bool:
        """Internal set implementation."""
        start_time = time.time()
        
        try:
            # Use default TTL if not specified
            if ttl is None:
                ttl = self._get_default_ttl(key)
            
            # Serialize value
            if isinstance(value, BaseModel):
                serialized = self.serializer.serialize(value)
            else:
                # For simple types, let Redis handle serialization
                serialized = value
            
            # Set with expiration
            if ttl:
                result = await self.connection_manager.client.setex(key, ttl, serialized)
            else:
                result = await self.connection_manager.client.set(key, serialized)
            
            return bool(result)
            
        except Exception as e:
            self.metrics.record_error("set", str(e))
            raise CacheError(f"Failed to set key {key}: {e}")
        finally:
            duration = time.time() - start_time
            self.metrics.record_operation_time("set", duration)
    
    async def delete(self, key: str) -> bool:
        """Remove value from cache."""
        await self._ensure_initialized()
        return await self._circuit_breaker.call(self._delete_impl, key)
    
    async def _delete_impl(self, key: str) -> bool:
        """Internal delete implementation."""
        try:
            result = await self.connection_manager.client.delete(key)
            return result > 0
        except Exception as e:
            self.metrics.record_error("delete", str(e))
            raise CacheError(f"Failed to delete key {key}: {e}")
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        await self._ensure_initialized()
        try:
            result = await self.connection_manager.client.exists(key)
            return result > 0
        except Exception as e:
            self.metrics.record_error("exists", str(e))
            return False
    
    async def flush(self, pattern: Optional[str] = None) -> int:
        """Flush cache keys matching pattern."""
        await self._ensure_initialized()
        
        try:
            if pattern is None:
                # Flush all keys (use with caution)
                await self.connection_manager.client.flushdb()
                return -1  # Unknown count
            else:
                # Use SCAN to find matching keys
                count = 0
                async for key in self._scan_keys(pattern):
                    if await self.delete(key):
                        count += 1
                return count
                
        except Exception as e:
            self.metrics.record_error("flush", str(e))
            raise CacheError(f"Failed to flush keys: {e}")
    
    async def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for key."""
        await self._ensure_initialized()
        
        try:
            ttl = await self.connection_manager.client.ttl(key)
            return ttl if ttl >= 0 else None
        except Exception as e:
            self.metrics.record_error("get_ttl", str(e))
            return None
    
    async def extend_ttl(self, key: str, ttl: int) -> bool:
        """Extend TTL for existing key."""
        await self._ensure_initialized()
        
        try:
            result = await self.connection_manager.client.expire(key, ttl)
            return bool(result)
        except Exception as e:
            self.metrics.record_error("extend_ttl", str(e))
            return False
    
    async def multi_get(
        self, 
        keys: List[str],
        model_class: Optional[Type[BaseModel]] = None
    ) -> Dict[str, Optional[T]]:
        """Get multiple keys efficiently using pipeline."""
        await self._ensure_initialized()
        
        if not keys:
            return {}
        
        # Batch keys for efficiency
        batch_size = 100
        results = {}
        
        for i in range(0, len(keys), batch_size):
            batch = keys[i:i + batch_size]
            batch_results = await self._multi_get_batch(batch, model_class)
            results.update(batch_results)
        
        return results
    
    async def _multi_get_batch(
        self, 
        keys: List[str],
        model_class: Optional[Type[BaseModel]] = None
    ) -> Dict[str, Optional[T]]:
        """Execute single batch get operation."""
        try:
            # Use MGET for efficiency
            values = await self.connection_manager.client.mget(keys)
            
            results = {}
            for key, value in zip(keys, values):
                if value is not None:
                    if model_class and isinstance(value, bytes):
                        results[key] = self.serializer.deserialize(value, model_class)
                    else:
                        results[key] = value
                    self.metrics.record_hit(key)
                else:
                    results[key] = None
                    self.metrics.record_miss(key)
            
            return results
            
        except Exception as e:
            self.metrics.record_error("multi_get", str(e))
            # Return empty results on error
            return {key: None for key in keys}
    
    async def multi_set(self, items: Dict[str, T], ttl: Optional[int] = None) -> bool:
        """Set multiple keys efficiently using pipeline."""
        await self._ensure_initialized()
        
        if not items:
            return True
        
        try:
            async with self.connection_manager.client.pipeline() as pipe:
                for key, value in items.items():
                    # Serialize if needed
                    if isinstance(value, BaseModel):
                        serialized = self.serializer.serialize(value)
                    else:
                        serialized = value
                    
                    # Use default TTL if not specified
                    if ttl is None:
                        key_ttl = self._get_default_ttl(key)
                    else:
                        key_ttl = ttl
                    
                    if key_ttl:
                        pipe.setex(key, key_ttl, serialized)
                    else:
                        pipe.set(key, serialized)
                
                results = await pipe.execute()
                return all(results)
                
        except Exception as e:
            self.metrics.record_error("multi_set", str(e))
            return False
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Atomic increment operation."""
        await self._ensure_initialized()
        
        try:
            result = await self.connection_manager.client.incrby(key, amount)
            return result
        except Exception as e:
            self.metrics.record_error("increment", str(e))
            raise CacheError(f"Failed to increment key {key}: {e}")
    
    async def set_if_not_exists(self, key: str, value: T, ttl: Optional[int] = None) -> bool:
        """Set value only if key doesn't exist."""
        await self._ensure_initialized()
        
        try:
            # Serialize if needed
            if isinstance(value, BaseModel):
                serialized = self.serializer.serialize(value)
            else:
                serialized = value
            
            # Use default TTL if not specified
            if ttl is None:
                ttl = self._get_default_ttl(key)
            
            # Use SET with NX option
            result = await self.connection_manager.client.set(
                key, serialized, nx=True, ex=ttl
            )
            
            return bool(result)
            
        except Exception as e:
            self.metrics.record_error("set_if_not_exists", str(e))
            return False
    
    async def health_check(self) -> bool:
        """Check cache health."""
        return await self.connection_manager.health_check()
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = self.metrics.get_stats()
        
        # Add Redis-specific stats
        try:
            info = await self.connection_manager.client.info()
            stats["redis"] = {
                "version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory": info.get("used_memory_human"),
                "used_memory_peak": info.get("used_memory_peak_human"),
                "evicted_keys": info.get("evicted_keys", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }
        except Exception as e:
            logger.error(f"Failed to get Redis info: {e}")
            stats["redis"] = {"error": str(e)}
        
        return stats
    
    def _get_default_ttl(self, key: str) -> int:
        """Get default TTL based on key prefix."""
        for prefix, ttl in self._default_ttls.items():
            if key.startswith(prefix):
                return ttl
        return 3600  # Default 1 hour
    
    async def _scan_keys(self, pattern: str, count: int = 100):
        """Scan keys matching pattern."""
        cursor = 0
        while True:
            cursor, keys = await self.connection_manager.client.scan(
                cursor, match=pattern, count=count
            )
            for key in keys:
                yield key
            if cursor == 0:
                break
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self.connection_manager:
            await self.connection_manager.close()