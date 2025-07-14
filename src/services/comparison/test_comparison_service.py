"""
Test script for the Comparison Service

Simple test to verify the core functionality works correctly.
"""

import asyncio
import logging
from decimal import Decimal

from ...services.weight_processor import WeightProcessor
from .comparison_service import create_comparison_service
from .cache_service import MemoryCache
from .provider_factory import SimpleAIProviderFactory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockConfig:
    """Mock configuration for testing"""
    
    def get_section(self, path: str, default=None):
        config_map = {
            "comparison_service.performance.provider_timeout_ms": 2000,
            "comparison_service.performance.cache_ttl_seconds": 300,
            "comparison_service.provider_selection.strategy": "cost_optimized",
            "comparison_service.provider_selection.fallback_chain": ["anthropic", "openai", "xai"],
            "safety.blocked_terms": [],
            "safety.sensitive_categories": [],
            "ab_tests": {}
        }
        return config_map.get(path, default)


class MockMetrics:
    """Mock metrics collector for testing"""
    
    def increment(self, metric_name: str, tags: dict = None):
        logger.info(f"Metric increment: {metric_name} {tags or {}}")
        
    def histogram(self, metric_name: str, value: float, tags: dict = None):
        logger.info(f"Metric histogram: {metric_name}={value} {tags or {}}")


async def test_comparison_service():
    """Test the comparison service with various weights"""
    
    logger.info("Starting Comparison Service test...")
    
    # Create dependencies
    weight_processor = WeightProcessor()
    provider_factory = SimpleAIProviderFactory()
    cache_service = MemoryCache()
    config = MockConfig()
    metrics = MockMetrics()
    
    # Create comparison service
    service = create_comparison_service(
        weight_processor=weight_processor,
        provider_factory=provider_factory,
        cache_service=cache_service,
        config=config,
        metrics=metrics,
        logger=logger
    )
    
    # Test cases
    test_weights = [
        "5 kg",
        "100 grams",
        "2.5 pounds",
        "1500 kg"
    ]
    
    for weight in test_weights:
        try:
            logger.info(f"\n--- Testing weight: {weight} ---")
            
            response = await service.create_comparison(
                weight_input=weight,
                comparison_style="default",
                include_visualization=True
            )
            
            logger.info(f"Weight: {response.weight_value} {response.weight_unit.value}")
            logger.info(f"Category: {response.weight_category.value}")
            logger.info(f"Comparison: {response.comparison_text}")
            logger.info(f"Objects: {response.comparison_objects}")
            logger.info(f"Provider: {response.metadata.provider_used}")
            logger.info(f"Confidence: {response.metadata.confidence_score}")
            
            if response.visualization_prompt:
                logger.info(f"Visualization: {response.visualization_prompt}")
                
        except Exception as e:
            logger.error(f"Test failed for {weight}: {e}")
            
    # Test caching
    logger.info("\n--- Testing cache functionality ---")
    
    # Same weight should hit cache
    response1 = await service.create_comparison("5 kg")
    response2 = await service.create_comparison("5 kg")
    
    logger.info(f"First call cache hit: {response1.metadata.cache_hit}")
    logger.info(f"Second call cache hit: {response2.metadata.cache_hit}")
    
    # Test provider fallback
    logger.info("\n--- Testing provider fallback ---")
    
    # Disable primary provider
    provider_factory.set_provider_availability("anthropic", False)
    
    try:
        response = await service.create_comparison("10 kg")
        logger.info(f"Fallback provider used: {response.metadata.provider_used}")
    except Exception as e:
        logger.error(f"Fallback test failed: {e}")
        
    # Cleanup
    cache_service.close()
    
    logger.info("\nComparison Service test completed!")


if __name__ == "__main__":
    asyncio.run(test_comparison_service())