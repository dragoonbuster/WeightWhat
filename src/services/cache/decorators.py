"""
Caching decorators for SizeComparator

This module provides decorators for automatic caching of function results,
with support for TTL, key generation, and invalidation patterns.
"""

import asyncio
import functools
import inspect
import logging
from typing import Any, Callable, Optional, Union, Dict, List, TypeVar, Type
from datetime import timedelta
import hashlib
import json

from .base import CacheService
from .key_builder import CacheKeyBuilder
from pydantic import BaseModel

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


def cache_result(
    ttl: Optional[Union[int, timedelta]] = None,
    key_prefix: Optional[str] = None,
    key_builder: Optional[Callable] = None,
    exclude_args: Optional[List[str]] = None,
    model_class: Optional[Type[BaseModel]] = None,
    condition: Optional[Callable] = None,
    cache_none: bool = False
):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds or timedelta
        key_prefix: Prefix for cache keys
        key_builder: Custom key building function
        exclude_args: Arguments to exclude from key generation
        model_class: Pydantic model class for deserialization
        condition: Function to determine if result should be cached
        cache_none: Whether to cache None results
        
    Usage:
        @cache_result(ttl=3600, key_prefix="ai_response")
        async def generate_comparison(weight1, weight2):
            return await ai_provider.generate(weight1, weight2)
        
        @cache_result(
            ttl=300,
            key_builder=lambda args, kwargs: f"custom:{args[0].id}",
            model_class=ProcessedWeight
        )
        async def process_weight(weight_input):
            return weight_processor.process(weight_input)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Get cache service instance
            cache = await _get_cache_service()
            if not cache:
                # No cache available, execute function directly
                return await func(*args, **kwargs)
            
            # Generate cache key
            cache_key = _generate_cache_key(
                func, args, kwargs, key_prefix, key_builder, exclude_args
            )
            
            try:
                # Try to get from cache
                cached_result = await cache.get(cache_key, model_class)
                if cached_result is not None:
                    logger.debug(f"Cache hit for key: {cache_key}")
                    return cached_result
                
                logger.debug(f"Cache miss for key: {cache_key}")
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Check if we should cache this result
                should_cache = True
                if condition and not await _call_condition(condition, result, *args, **kwargs):
                    should_cache = False
                elif not cache_none and result is None:
                    should_cache = False
                
                if should_cache:
                    # Convert ttl to seconds
                    ttl_seconds = _convert_ttl_to_seconds(ttl)
                    
                    # Cache the result
                    await cache.set(cache_key, result, ttl_seconds)
                    logger.debug(f"Cached result for key: {cache_key}")
                
                return result
                
            except Exception as e:
                logger.error(f"Cache error for key {cache_key}: {e}")
                # If cache fails, still execute the function
                return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, we need to run in an event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            return loop.run_until_complete(async_wrapper(*args, **kwargs))
        
        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def invalidate_cache(
    key_pattern: Optional[str] = None,
    key_builder: Optional[Callable] = None,
    related_patterns: Optional[List[str]] = None
):
    """
    Decorator for invalidating cache entries after function execution.
    
    Args:
        key_pattern: Glob pattern for keys to invalidate
        key_builder: Custom key building function for invalidation
        related_patterns: Additional patterns to invalidate
        
    Usage:
        @invalidate_cache(key_pattern="ai_response:*")
        async def update_ai_model():
            # Update AI model configuration
            pass
        
        @invalidate_cache(
            key_builder=lambda args, kwargs: f"weight:{args[0].id}:*"
        )
        async def update_weight(weight_id, new_data):
            # Update weight data
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Execute function first
            result = await func(*args, **kwargs)
            
            # Get cache service
            cache = await _get_cache_service()
            if not cache:
                return result
            
            try:
                # Build invalidation patterns
                patterns = []
                
                if key_pattern:
                    patterns.append(key_pattern)
                
                if key_builder:
                    custom_pattern = await _call_key_builder(key_builder, args, kwargs)
                    if custom_pattern:
                        patterns.append(custom_pattern)
                
                if related_patterns:
                    patterns.extend(related_patterns)
                
                # Invalidate matching keys
                for pattern in patterns:
                    count = await cache.flush(pattern)
                    logger.info(f"Invalidated {count} keys matching pattern: {pattern}")
                
            except Exception as e:
                logger.error(f"Cache invalidation error: {e}")
                # Don't fail the function if invalidation fails
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            return loop.run_until_complete(async_wrapper(*args, **kwargs))
        
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def cache_ai_response(
    ttl: int = 86400,  # 24 hours default
    provider_arg: str = "provider",
    model_arg: str = "model"
):
    """
    Specialized decorator for caching AI provider responses.
    
    Args:
        ttl: Time to live in seconds
        provider_arg: Name of provider argument
        model_arg: Name of model argument
        
    Usage:
        @cache_ai_response(ttl=3600)
        async def generate_comparison(weight1, weight2, provider="openai", model="gpt-4"):
            return await ai_provider.generate(weight1, weight2)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache = await _get_cache_service()
            if not cache:
                return await func(*args, **kwargs)
            
            # Get function signature
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Extract provider and model
            provider = bound_args.arguments.get(provider_arg, "unknown")
            model = bound_args.arguments.get(model_arg, "unknown")
            
            # Generate content hash for cache key
            cache_content = {
                "args": [str(arg) for arg in args],
                "kwargs": {k: str(v) for k, v in kwargs.items()}
            }
            content_hash = CacheKeyBuilder.generate_content_hash(cache_content)
            
            # Build AI response cache key
            cache_key = CacheKeyBuilder.build_ai_response_key(
                weight=None,  # Will be extracted from args if needed
                provider=provider,
                model=model,
                prompt_hash=content_hash[:16]
            )
            
            try:
                # Check cache
                cached_result = await cache.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"AI response cache hit: {cache_key}")
                    return cached_result
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Cache result
                await cache.set(cache_key, result, ttl)
                logger.debug(f"Cached AI response: {cache_key}")
                
                return result
                
            except Exception as e:
                logger.error(f"AI response cache error: {e}")
                return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def cache_weight_processing(
    ttl: int = 3600,  # 1 hour default
    operation: str = "process"
):
    """
    Specialized decorator for caching weight processing results.
    
    Args:
        ttl: Time to live in seconds
        operation: Processing operation name
        
    Usage:
        @cache_weight_processing(operation="normalize")
        async def normalize_weight(weight_str):
            return weight_processor.normalize(weight_str)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache = await _get_cache_service()
            if not cache:
                return await func(*args, **kwargs)
            
            # Get first argument as weight string
            weight_str = str(args[0]) if args else "unknown"
            
            # Build weight processing cache key
            cache_key = CacheKeyBuilder.build_weight_key(
                weight_str=weight_str,
                operation=operation
            )
            
            try:
                # Check cache
                from src.models.weight import ProcessedWeight
                cached_result = await cache.get(cache_key, ProcessedWeight)
                if cached_result is not None:
                    logger.debug(f"Weight processing cache hit: {cache_key}")
                    return cached_result
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Cache result
                await cache.set(cache_key, result, ttl)
                logger.debug(f"Cached weight processing result: {cache_key}")
                
                return result
                
            except Exception as e:
                logger.error(f"Weight processing cache error: {e}")
                return await func(*args, **kwargs)
        
        return wrapper
    
    return decorator


# Helper functions

async def _get_cache_service() -> Optional[CacheService]:
    """Get cache service instance."""
    try:
        # Try to get from application context first
        # This would be set up during application initialization
        import contextvars
        cache_context = contextvars.ContextVar('cache_service', default=None)
        cache = cache_context.get()
        
        if cache is None:
            # Fallback to creating new instance
            cache = CacheService.from_env()
            cache_context.set(cache)
        
        return cache
    except Exception as e:
        logger.error(f"Failed to get cache service: {e}")
        return None


def _generate_cache_key(
    func: Callable,
    args: tuple,
    kwargs: dict,
    key_prefix: Optional[str],
    key_builder: Optional[Callable],
    exclude_args: Optional[List[str]]
) -> str:
    """Generate cache key for function call."""
    if key_builder:
        return key_builder(args, kwargs)
    
    # Build key from function name and arguments
    func_name = f"{func.__module__}.{func.__name__}"
    
    # Filter arguments
    if exclude_args:
        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())
        
        # Build filtered args and kwargs
        filtered_args = []
        filtered_kwargs = {}
        
        for i, arg in enumerate(args):
            param_name = param_names[i] if i < len(param_names) else f"arg_{i}"
            if param_name not in exclude_args:
                filtered_args.append(arg)
        
        for key, value in kwargs.items():
            if key not in exclude_args:
                filtered_kwargs[key] = value
        
        args = tuple(filtered_args)
        kwargs = filtered_kwargs
    
    # Create hash of arguments
    arg_data = {
        "args": [str(arg) for arg in args],
        "kwargs": {k: str(v) for k, v in sorted(kwargs.items())}
    }
    
    arg_hash = CacheKeyBuilder.generate_content_hash(arg_data, "md5")[:12]
    
    # Build final key
    if key_prefix:
        return f"{key_prefix}:{func_name}:{arg_hash}"
    else:
        return f"func:{func_name}:{arg_hash}"


def _convert_ttl_to_seconds(ttl: Optional[Union[int, timedelta]]) -> Optional[int]:
    """Convert TTL to seconds."""
    if ttl is None:
        return None
    elif isinstance(ttl, timedelta):
        return int(ttl.total_seconds())
    else:
        return int(ttl)


async def _call_condition(condition: Callable, result: Any, *args, **kwargs) -> bool:
    """Call condition function with proper async handling."""
    try:
        if inspect.iscoroutinefunction(condition):
            return await condition(result, *args, **kwargs)
        else:
            return condition(result, *args, **kwargs)
    except Exception as e:
        logger.error(f"Condition function error: {e}")
        return True  # Default to caching if condition fails


async def _call_key_builder(key_builder: Callable, args: tuple, kwargs: dict) -> Optional[str]:
    """Call key builder function with proper async handling."""
    try:
        if inspect.iscoroutinefunction(key_builder):
            return await key_builder(args, kwargs)
        else:
            return key_builder(args, kwargs)
    except Exception as e:
        logger.error(f"Key builder function error: {e}")
        return None


# Context manager for temporary cache configuration

class CacheContext:
    """Context manager for temporary cache configuration."""
    
    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service
        self._old_cache = None
        
    async def __aenter__(self):
        # Set cache service in context
        import contextvars
        cache_context = contextvars.ContextVar('cache_service', default=None)
        self._old_cache = cache_context.get()
        cache_context.set(self.cache_service)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Restore old cache service
        import contextvars
        cache_context = contextvars.ContextVar('cache_service', default=None)
        cache_context.set(self._old_cache)