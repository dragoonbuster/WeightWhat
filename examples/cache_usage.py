#!/usr/bin/env python3
"""
Example usage of the SizeComparator Cache Service

This example demonstrates how to use the cache service for:
- AI response caching
- Weight processing caching
- Configuration caching
- Custom data caching
"""

import asyncio
import sys
import os
from datetime import datetime
from decimal import Decimal

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.cache import CacheService, cache_result, cache_ai_response, cache_weight_processing
from models.weight import ProcessedWeight, WeightInput, WeightUnit
from models.providers import AIProviderResponse, AIProviderMetadata
from models.config import CachedConfig


async def basic_cache_operations():
    """Demonstrate basic cache operations."""
    print("=== Basic Cache Operations ===")
    
    # Create cache service from environment
    cache = CacheService.from_env()
    
    # Store simple values
    await cache.set("hello", "world", ttl=60)
    await cache.set("counter", 42, ttl=300)
    
    # Retrieve values
    greeting = await cache.get("hello")
    count = await cache.get("counter")
    
    print(f"Greeting: {greeting}")
    print(f"Count: {count}")
    
    # Check if keys exist
    exists = await cache.exists("hello")
    print(f"'hello' key exists: {exists}")
    
    # Get TTL
    ttl = await cache.get_ttl("hello")
    print(f"TTL for 'hello': {ttl} seconds")
    
    # Multi-operations
    items = {
        "item1": "value1",
        "item2": "value2",
        "item3": "value3"
    }
    await cache.multi_set(items, ttl=120)
    
    results = await cache.multi_get(["item1", "item2", "item3", "missing"])
    print(f"Multi-get results: {results}")
    
    # Atomic operations
    new_count = await cache.increment("counter", 5)
    print(f"Incremented counter: {new_count}")
    
    # Conditional set
    was_set = await cache.set_if_not_exists("counter", 100)
    print(f"Set if not exists (should be False): {was_set}")
    
    print()


async def pydantic_model_caching():
    """Demonstrate caching of Pydantic models."""
    print("=== Pydantic Model Caching ===")
    
    cache = CacheService.from_env()
    
    # Create a ProcessedWeight model
    weight = ProcessedWeight(
        original_input=WeightInput(
            value="10.5 kg",
            confidence=0.95
        ),
        parsed_value=Decimal("10.5"),
        display_value="10.5 kg",
        unit_used=WeightUnit.KILOGRAM,
        conversion_factor=Decimal("1.0"),
        parsing_confidence=0.95,
        validation_warnings=[]
    )
    
    # Cache the model
    await cache.set("weight:elephant", weight, ttl=3600)
    
    # Retrieve the model
    cached_weight = await cache.get("weight:elephant", ProcessedWeight)
    print(f"Cached weight: {cached_weight.display_value}")
    print(f"Confidence: {cached_weight.parsing_confidence}")
    
    # Create AI response model
    ai_response = AIProviderResponse(
        content="An elephant weighs about 3 times as much as a small car",
        confidence_score=0.92,
        metadata=AIProviderMetadata(
            provider_name="openai",
            model_name="gpt-4",
            response_time_ms=245,
            tokens_used=156,
            cost_estimate=Decimal("0.0031")
        ),
        validation_passed=True,
        validation_errors=[],
        fallback_used=False
    )
    
    # Cache AI response
    await cache.set("ai:comparison:elephant_vs_car", ai_response, ttl=86400)
    
    # Retrieve AI response
    cached_ai = await cache.get("ai:comparison:elephant_vs_car", AIProviderResponse)
    print(f"AI response: {cached_ai.content[:50]}...")
    print(f"Provider: {cached_ai.metadata.provider_name}")
    print(f"Cost: ${cached_ai.metadata.cost_estimate}")
    
    print()


@cache_result(ttl=300, key_prefix="expensive_calculation")
async def expensive_calculation(base: int, multiplier: int) -> int:
    """Simulate an expensive calculation with caching."""
    print(f"Performing expensive calculation: {base} * {multiplier}")
    await asyncio.sleep(0.5)  # Simulate work
    return base * multiplier


@cache_ai_response(ttl=3600)
async def generate_comparison(weight1: str, weight2: str, provider="openai", model="gpt-4"):
    """Simulate AI comparison generation with caching."""
    print(f"Calling AI provider {provider} with model {model}")
    await asyncio.sleep(1.0)  # Simulate API call
    
    return f"A {weight1} object is roughly equivalent to {weight2} in weight"


@cache_weight_processing(operation="normalize")
async def normalize_weight(weight_str: str) -> ProcessedWeight:
    """Simulate weight processing with caching."""
    print(f"Processing weight: {weight_str}")
    await asyncio.sleep(0.2)  # Simulate processing
    
    return ProcessedWeight(
        original_input=WeightInput(value=weight_str, confidence=1.0),
        parsed_value=Decimal("100.0"),
        display_value="100.0 kg",
        unit_used=WeightUnit.KILOGRAM,
        conversion_factor=Decimal("1.0"),
        parsing_confidence=1.0,
        validation_warnings=[]
    )


async def decorator_examples():
    """Demonstrate caching decorators."""
    print("=== Caching Decorators ===")
    
    # Test expensive calculation caching
    print("First call (should calculate):")
    result1 = await expensive_calculation(10, 5)
    print(f"Result: {result1}")
    
    print("\nSecond call (should use cache):")
    result2 = await expensive_calculation(10, 5)
    print(f"Result: {result2}")
    
    # Test AI response caching
    print("\nFirst AI call (should call provider):")
    ai_result1 = await generate_comparison("elephant", "car")
    print(f"AI Result: {ai_result1}")
    
    print("\nSecond AI call (should use cache):")
    ai_result2 = await generate_comparison("elephant", "car")
    print(f"AI Result: {ai_result2}")
    
    # Test weight processing caching
    print("\nFirst weight processing (should process):")
    weight1 = await normalize_weight("100 kg")
    print(f"Weight: {weight1.display_value}")
    
    print("\nSecond weight processing (should use cache):")
    weight2 = await normalize_weight("100 kg")
    print(f"Weight: {weight2.display_value}")
    
    print()


async def cache_stats_and_health():
    """Demonstrate cache statistics and health monitoring."""
    print("=== Cache Statistics and Health ===")
    
    cache = CacheService.from_env()
    
    # Get cache statistics
    stats = await cache.get_stats()
    print("Cache Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Health check
    is_healthy = await cache.health_check()
    print(f"\nCache Health: {' Healthy' if is_healthy else ' Unhealthy'}")
    
    print()


async def cache_invalidation():
    """Demonstrate cache invalidation patterns."""
    print("=== Cache Invalidation ===")
    
    cache = CacheService.from_env()
    
    # Set some test data
    await cache.set("user:123:profile", {"name": "John", "age": 30}, ttl=300)
    await cache.set("user:123:settings", {"theme": "dark"}, ttl=300)
    await cache.set("user:456:profile", {"name": "Jane", "age": 25}, ttl=300)
    await cache.set("config:appersion", "1.0.0", ttl=300)
    
    print("Keys before invalidation:")
    for key in ["user:123:profile", "user:123:settings", "user:456:profile", "config:appersion"]:
        exists = await cache.exists(key)
        print(f"  {key}: {'exists' if exists else 'missing'}")
    
    # Invalidate user 123's data
    invalidated = await cache.flush("user:123")
    print(f"\nInvalidated {invalidated} keys matching 'user:123'")
    
    print("\nKeys after invalidation:")
    for key in ["user:123:profile", "user:123:settings", "user:456:profile", "config:appersion"]:
        exists = await cache.exists(key)
        print(f"  {key}: {'exists' if exists else 'missing'}")
    
    print()


async def main():
    """Run all cache examples."""
    print("SizeComparator Cache Service Examples")
    print("=" * 40)
    
    try:
        await basic_cache_operations()
        await pydantic_model_caching()
        await decorator_examples()
        await cache_stats_and_health()
        await cache_invalidation()
        
        print("All examples completed successfully! ")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())