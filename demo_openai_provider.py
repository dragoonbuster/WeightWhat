#!/usr/bin/env python3
"""
Demo script for OpenAI Provider implementation.

This script demonstrates how to use the OpenAI provider for weight comparisons
following the OPENAI_PROVIDER_SPEC.md requirements.
"""

import asyncio
import os
import logging
from uuid import uuid4

from src.providers.openai_provider import OpenAIProvider
from src.models.providers import AIProviderRequest, TemplateVariables
from src.core.environment import APIProviderConfigInterface

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DemoEnvironmentConfig(APIProviderConfigInterface):
    """Demo environment configuration for OpenAI provider."""
    
    def __init__(self):
        self.api_key = os.getenv("SIZECOMPARATOR_OPENAI_API_KEY")
        
    def get_component_config(self):
        return {
            "api_key": self.api_key,
            "endpoint": "https://api.openai.com/v1",
            "model": "gpt-4",
            "timeout_seconds": 30
        }
    
    def get_api_key(self):
        return self.api_key
    
    def get_endpoint_url(self):
        return "https://api.openai.com/v1"
    
    def on_config_change(self, variable_name, new_value):
        pass


async def demo_weight_comparison():
    """Demonstrate weight comparison using OpenAI provider."""
    
    # Check if API key is available
    api_key = os.getenv("SIZECOMPARATOR_OPENAI_API_KEY")
    if not api_key:
        logger.error("SIZECOMPARATOR_OPENAI_API_KEY not found. Please set your OpenAI API key.")
        logger.info("Example: export SIZECOMPARATOR_OPENAI_API_KEY='sk-your-key-here'")
        return
    
    # Configuration for OpenAI provider
    config = {
        "api_key": api_key,
        "endpoint": "https://api.openai.com/v1",
        "model": "gpt-4",
        "timeout_seconds": 30.0,
        "max_tokens": 500,
        "temperature": 0.3,
        "rate_limit_rpm": 3500,
        "max_retries": 3,
        "structured_output": True,
        "enable_caching": True,
        "cache_ttl_seconds": 3600
    }
    
    # Create environment config interface
    env_config = DemoEnvironmentConfig()
    
    # Initialize the OpenAI provider
    provider = OpenAIProvider(config, logger, env_config)
    
    try:
        # Initialize the provider
        logger.info("Initializing OpenAI provider...")
        await provider.initialize()
        
        # Perform health check
        logger.info("Performing health check...")
        health = await provider.health_check()
        logger.info(f"Provider health: {health.status}")
        
        # Create a demo weight comparison request
        template_variables = TemplateVariables(
            item1_name="African Elephant",
            item1_weight="5000 kg",
            item2_name="Tesla Model 3",
            item2_weight="1611 kg",
            weight_ratio=5000 / 1611,
            percentage_difference=((5000 - 1611) / 1611) * 100,
            heavier_item="item1",
            comparison_category="animal_vs_vehicle",
            significance_level="moderate",
            output_unit="kg",
            locale="en-US"
        )
        
        request = AIProviderRequest(
            prompt_template_id="weight_comparison_standard",
            template_variables=template_variables.dict(),
            weight_data={
                "item1": {"name": "African Elephant", "weight": "5000 kg"},
                "item2": {"name": "Tesla Model 3", "weight": "1611 kg"}
            },
            max_tokens=500,
            temperature=0.3,
            timeout_seconds=30.0,
            request_id=uuid4(),
            retry_count=0
        )
        
        # Generate the comparison
        logger.info("Generating weight comparison...")
        logger.info(f"Comparing: {template_variables.item1_name} vs {template_variables.item2_name}")
        
        response = await provider.generate_comparison(request)
        
        # Display results
        logger.info("=" * 60)
        logger.info("WEIGHT COMPARISON RESULTS")
        logger.info("=" * 60)
        
        logger.info(f"Item 1: {response.item1.display_value}")
        logger.info(f"Item 2: {response.item2.display_value}")
        
        logger.info(f"Weight Ratio: {response.analysis.weight_ratio:.2f}")
        logger.info(f"Percentage Difference: {response.analysis.percentage_difference:.1f}%")
        logger.info(f"Heavier Item: {response.analysis.heavier_item}")
        logger.info(f"Significance: {response.analysis.significance_level}")
        logger.info(f"Category: {response.analysis.comparison_category}")
        
        if response.visualization:
            logger.info("\nVisualization Prompt:")
            logger.info(f"'{response.visualization.prompt_text}'")
            logger.info(f"Provider: {response.visualization.provider_used}")
            logger.info(f"Confidence: {response.visualization.confidence_score:.2f}")
        
        # Display metadata
        logger.info("\nMetadata:")
        logger.info(f"Request ID: {response.metadata.request_id}")
        logger.info(f"Processing Time: {response.metadata.processing_time_ms}ms")
        logger.info(f"AI Provider: {response.metadata.ai_provider_used}")
        logger.info(f"Cache Hit: {response.metadata.cache_hit}")
        logger.info(f"API Version: {response.metadata.api_version}")
        
        # Display provider statistics
        logger.info("\nProvider Statistics:")
        rate_stats = provider.rate_limiter.get_rate_limit_stats()
        cache_stats = provider.response_cache.get_cache_stats()
        token_stats = provider.token_tracker.get_usage_stats(1)
        
        logger.info(f"Rate Limit Utilization: {rate_stats['utilization_percentage']:.1f}%")
        logger.info(f"Cache Hit Rate: {cache_stats['hit_rate']:.3f}")
        if not token_stats.get('error'):
            logger.info(f"Tokens Used: {token_stats['total_tokens']}")
            logger.info(f"Estimated Cost: ${token_stats['total_cost_usd']:.4f}")
        
        # Test caching by making the same request again
        logger.info("\nTesting cache with identical request...")
        cached_response = await provider.generate_comparison(request)
        cache_stats_after = provider.response_cache.get_cache_stats()
        
        if cache_stats_after['hit_rate'] > cache_stats['hit_rate']:
            logger.info("✓ Cache working correctly - hit rate increased")
        else:
            logger.info("ℹ Cache miss (expected for first run)")
        
        # Test different comparison
        logger.info("\nTesting different comparison...")
        
        template_variables2 = TemplateVariables(
            item1_name="Blue Whale",
            item1_weight="150000 kg",
            item2_name="Boeing 747",
            item2_weight="183000 kg",
            weight_ratio=150000 / 183000,
            percentage_difference=((183000 - 150000) / 150000) * 100,
            heavier_item="item2",
            comparison_category="animal_vs_vehicle",
            significance_level="small",
            output_unit="kg",
            locale="en-US"
        )
        
        request2 = AIProviderRequest(
            prompt_template_id="weight_comparison_standard",
            template_variables=template_variables2.dict(),
            weight_data={
                "item1": {"name": "Blue Whale", "weight": "150000 kg"},
                "item2": {"name": "Boeing 747", "weight": "183000 kg"}
            },
            max_tokens=500,
            temperature=0.3,
            timeout_seconds=30.0,
            request_id=uuid4(),
            retry_count=0
        )
        
        response2 = await provider.generate_comparison(request2)
        
        logger.info(f"Second Comparison: {template_variables2.item1_name} vs {template_variables2.item2_name}")
        logger.info(f"Result: {response2.analysis.heavier_item} is heavier by {response2.analysis.percentage_difference:.1f}%")
        
        # Final health check
        final_health = await provider.health_check()
        logger.info(f"\nFinal Provider Health: {final_health.status}")
        logger.info(f"Success Rate: {final_health.success_rate:.3f}")
        logger.info(f"Average Response Time: {final_health.avg_response_time_ms:.1f}ms")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Shutdown the provider
        await provider.shutdown()
        logger.info("OpenAI provider demo completed")


async def demo_error_handling():
    """Demonstrate error handling and circuit breaker functionality."""
    
    logger.info("\n" + "=" * 60)
    logger.info("TESTING ERROR HANDLING")
    logger.info("=" * 60)
    
    # Create provider with invalid API key to test error handling
    config = {
        "api_key": "sk-invalid-key-for-testing",
        "endpoint": "https://api.openai.com/v1",
        "model": "gpt-4",
        "timeout_seconds": 5.0,  # Short timeout for faster testing
        "max_retries": 2,  # Fewer retries for demo
        "structured_output": True
    }
    
    provider = OpenAIProvider(config, logger)
    
    try:
        await provider.initialize()
        
        # This should fail due to invalid API key
        template_variables = TemplateVariables(
            item1_name="Test Item 1",
            item1_weight="1 kg",
            item2_name="Test Item 2", 
            item2_weight="2 kg",
            weight_ratio=0.5,
            percentage_difference=50.0,
            heavier_item="item2",
            comparison_category="test",
            significance_level="small",
            output_unit="kg",
            locale="en-US"
        )
        
        request = AIProviderRequest(
            prompt_template_id="test",
            template_variables=template_variables.dict(),
            weight_data={"test": "data"},
            request_id=uuid4()
        )
        
        try:
            await provider.generate_comparison(request)
        except Exception as e:
            logger.info(f"Expected error caught: {type(e).__name__}: {e}")
            
        # Check provider health after error
        health = await provider.health_check()
        logger.info(f"Provider health after error: {health.status}")
        
        # Check circuit breaker state
        circuit_state = provider._circuit_breaker.get_state()
        logger.info(f"Circuit breaker state: {circuit_state['state']}")
        logger.info(f"Failure count: {circuit_state['failure_count']}")
        
    except Exception as e:
        logger.info(f"Error handling demo completed with expected error: {e}")
    
    finally:
        await provider.shutdown()


async def main():
    """Main demo function."""
    logger.info("Starting OpenAI Provider Demo")
    logger.info("This demo showcases the OpenAI provider implementation")
    logger.info("following the OPENAI_PROVIDER_SPEC.md specification")
    
    try:
        # Run main demo
        await demo_weight_comparison()
        
        # Run error handling demo
        await demo_error_handling()
        
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())