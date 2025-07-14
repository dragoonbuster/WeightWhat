"""
Example usage of the Anthropic provider for SizeComparator.

This demonstrates how to initialize and use the Anthropic provider
for weight comparisons.
"""

import asyncio
import os
from decimal import Decimal

from .anthropic_provider import AnthropicProvider
from ..models.requests import WeightComparisonRequest
from ..models.weight import WeightInput


async def main():
    """Example usage of the Anthropic provider."""
    
    # Configuration for Anthropic provider
    config = {
        'api_key': os.getenv('SIZECOMPARATOR_ANTHROPIC_API_KEY'),
        'model': 'claude-3-sonnet-20240229',
        'intelligent_model_selection': True,
        'use_xml_tags': True,
        'safety_enabled': True,
        'beta_features': False,
        'timeout_seconds': 60.0,
        'rate_limit_rpm': 1000
    }
    
    # Check if API key is available
    if not config['api_key']:
        print("Please set SIZECOMPARATOR_ANTHROPIC_API_KEY environment variable")
        return
    
    # Initialize provider
    provider = AnthropicProvider(config)
    
    # Create a sample weight comparison request
    request = WeightComparisonRequest(
        item1="African Elephant",
        item1_weight=WeightInput(
            value="5000 kg",
            confidence=0.95,
            source="Wildlife Conservation Society"
        ),
        item2="Tesla Model 3",
        item2_weight=WeightInput(
            value=1611.0,
            unit="kg",
            confidence=1.0,
            source="Tesla Specifications"
        ),
        comparison_type="detailed",
        include_visualization=True
    )
    
    try:
        # Generate comparison
        print("Generating weight comparison...")
        response = await provider.generate_comparison(request)
        
        # Display results
        print("\n=== Weight Comparison Results ===")
        print(f"Item 1: {response.item1.name}")
        print(f"  Weight: {response.item1.display_value}")
        print(f"  Confidence: {response.item1.parsing_confidence}")
        
        print(f"\nItem 2: {response.item2.name}")
        print(f"  Weight: {response.item2.display_value}")
        print(f"  Confidence: {response.item2.parsing_confidence}")
        
        print(f"\nComparison:")
        print(f"  Ratio: {response.analysis.weight_ratio}")
        print(f"  Heavier item: {response.analysis.heavier_item}")
        print(f"  Significance: {response.analysis.significance_level}")
        print(f"  Category: {response.analysis.comparison_category}")
        
        if response.visualization:
            print(f"\nVisualization Prompt:")
            print(f"  {response.visualization.prompt_text}")
            print(f"  Provider: {response.visualization.provider_used}")
            print(f"  Confidence: {response.visualization.confidence_score}")
        
        # Check provider health
        health = provider.get_health()
        print(f"\n=== Provider Health ===")
        print(f"Status: {health.status}")
        print(f"Success Rate: {health.success_rate:.2%}")
        print(f"Circuit Breaker: {health.circuit_breaker_state}")
        
    except Exception as e:
        print(f"Error: {e}")
        
        # Check provider health after error
        health = provider.get_health()
        print(f"\nProvider Health after error:")
        print(f"Status: {health.status}")
        print(f"Error Count: {health.error_count}")
        print(f"Last Error: {health.last_error}")


if __name__ == "__main__":
    asyncio.run(main())