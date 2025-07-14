"""
Usage example for X.ai (Grok) provider.

This module demonstrates how to use the XAI provider for weight comparisons
with proper configuration, error handling, and monitoring.
"""

import asyncio
import os
from typing import Dict, Any
from uuid import uuid4

from .xai_provider import XAIProvider
from .xai_config_example import get_development_config, get_production_config
from ..models.providers import AIProviderRequest


async def create_xai_provider_example():
    """Create and configure an XAI provider instance."""
    
    # Get configuration based on environment
    environment = os.getenv("SIZECOMPARATOR_ENVIRONMENT", "development")
    
    if environment == "production":
        config = get_production_config()
    else:
        config = get_development_config()
    
    # Override API key if provided via environment variable
    api_key = os.getenv("SIZECOMPARATOR_XAI_API_KEY")
    if api_key:
        config["api_config"]["api_key"] = api_key
    
    # Create provider
    provider = XAIProvider(config)
    
    print(f"Created XAI provider with configuration for {environment}")
    print(f"Rate limit: {config['rate_limiting']['requests_per_minute']} RPM")
    print(f"Timeout: {config['reliability']['timeout_seconds']}s")
    print(f"Quality threshold: {config['quality_validation']['min_confidence_threshold']}")
    
    return provider


async def example_weight_comparison():
    """Example of performing a weight comparison with XAI provider."""
    
    # Create provider
    provider = await create_xai_provider_example()
    
    # Create comparison request
    request = AIProviderRequest(
        prompt_template_id="weight_comparison",
        template_variables={
            "item1_name": "elephant",
            "item1_weight": "5000 kg",
            "item2_name": "car",
            "item2_weight": "1500 kg",
            "comparison_category": "animal_vs_vehicle"
        },
        weight_data={
            "item1": {"value": "5000 kg"},
            "item2": {"value": "1500 kg"}
        },
        max_tokens=800,
        temperature=0.3,
        timeout_seconds=30.0,
        request_id=uuid4()
    )
    
    try:
        # Perform comparison
        print("Generating weight comparison...")
        response = await provider.generate_comparison(request)
        
        # Display results
        print("\n=== Comparison Results ===")
        print(f"Item 1: {response.item1.display_value} (confidence: {response.item1.confidence:.2f})")
        print(f"Item 2: {response.item2.display_value} (confidence: {response.item2.confidence:.2f})")
        print(f"Weight ratio: {response.analysis.weight_ratio:.2f}")
        print(f"Heavier item: {response.analysis.heavier_item}")
        print(f"Significance: {response.analysis.significance_level}")
        
        if response.visualization:
            print(f"\nVisualization prompt: {response.visualization.prompt_text[:100]}...")
            print(f"Visualization confidence: {response.visualization.confidence_score:.2f}")
        
        print(f"\nProcessing time: {response.metadata.processing_time_ms}ms")
        print(f"Provider used: {response.metadata.ai_provider_used}")
        
    except Exception as e:
        print(f"Comparison failed: {str(e)}")
        print(f"Error type: {type(e).__name__}")


async def example_health_check():
    """Example of checking XAI provider health."""
    
    # Create provider
    provider = await create_xai_provider_example()
    
    try:
        print("Performing health check...")
        health = await provider.health_check()
        
        print("\n=== Health Status ===")
        print(f"Provider: {health.provider_name}")
        print(f"Status: {health.status}")
        print(f"Circuit breaker: {health.circuit_breaker_state}")
        print(f"Success rate: {health.success_rate:.2%}")
        print(f"Average response time: {health.avg_response_time_ms:.2f}ms")
        print(f"Error count: {health.error_count}")
        print(f"Rate limit remaining: {health.rate_limit_quota}")
        
        if health.last_error:
            print(f"Last error: {health.last_error}")
        
    except Exception as e:
        print(f"Health check failed: {str(e)}")


async def example_batch_comparisons():
    """Example of performing multiple comparisons with rate limiting."""
    
    # Create provider
    provider = await create_xai_provider_example()
    
    # Define multiple comparison requests
    comparisons = [
        ("elephant", "5000 kg", "car", "1500 kg"),
        ("feather", "1 gram", "coin", "10 grams"),
        ("blue whale", "150 tons", "airplane", "80 tons"),
        ("phone", "200 grams", "book", "500 grams"),
        ("mountain", "1 billion tons", "building", "50000 tons")
    ]
    
    successful_comparisons = 0
    failed_comparisons = 0
    
    print(f"Performing {len(comparisons)} weight comparisons...")
    
    for i, (item1_name, item1_weight, item2_name, item2_weight) in enumerate(comparisons, 1):
        print(f"\nComparison {i}: {item1_name} vs {item2_name}")
        
        request = AIProviderRequest(
            prompt_template_id="weight_comparison",
            template_variables={
                "item1_name": item1_name,
                "item1_weight": item1_weight,
                "item2_name": item2_name,
                "item2_weight": item2_weight,
                "comparison_category": "mixed"
            },
            weight_data={
                "item1": {"value": item1_weight},
                "item2": {"value": item2_weight}
            },
            max_tokens=600,
            temperature=0.3,
            request_id=uuid4()
        )
        
        try:
            response = await provider.generate_comparison(request)
            successful_comparisons += 1
            
            print(f"  ✓ Ratio: {response.analysis.weight_ratio:.2f}")
            print(f"    Heavier: {response.analysis.heavier_item}")
            print(f"    Time: {response.metadata.processing_time_ms}ms")
            
        except Exception as e:
            failed_comparisons += 1
            print(f"  ✗ Failed: {str(e)}")
        
        # Small delay to respect rate limits
        await asyncio.sleep(1)
    
    print(f"\n=== Batch Results ===")
    print(f"Successful: {successful_comparisons}")
    print(f"Failed: {failed_comparisons}")
    print(f"Success rate: {successful_comparisons / len(comparisons):.2%}")


async def main():
    """Main example function."""
    print("X.ai (Grok) Provider Usage Examples")
    print("=" * 40)
    
    # Check if API key is available
    if not os.getenv("SIZECOMPARATOR_XAI_API_KEY"):
        print("Warning: SIZECOMPARATOR_XAI_API_KEY not set")
        print("Set your X.ai API key to run live examples")
        print("Examples will use mock configuration")
    
    try:
        # Example 1: Basic weight comparison
        print("\n1. Basic Weight Comparison")
        print("-" * 30)
        await example_weight_comparison()
        
        # Example 2: Health check
        print("\n2. Health Check")
        print("-" * 15)
        await example_health_check()
        
        # Example 3: Batch comparisons
        print("\n3. Batch Comparisons")
        print("-" * 20)
        await example_batch_comparisons()
        
    except KeyboardInterrupt:
        print("\nExamples interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
    
    print("\nExamples completed!")


if __name__ == "__main__":
    # Run examples
    asyncio.run(main())