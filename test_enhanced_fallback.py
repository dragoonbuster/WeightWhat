#!/usr/bin/env python3
"""
Test Enhanced Fallback Service

This script tests the enhanced fallback service functionality.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from src.services.enhanced_fallback_service import EnhancedFallbackService
from src.models.mvp import MVPComparisonRequest


async def test_enhanced_fallback():
    """Test the enhanced fallback service"""
    
    print("Testing Enhanced Fallback Service")
    print("=" * 50)
    
    # Create service
    service = EnhancedFallbackService()
    
    # Check health status
    health = await service.get_health_status()
    print(f"\nHealth Status: {health['status']}")
    print(f"Repository Loaded: {health['repository_loaded']}")
    print(f"Total Responses: {health['total_responses']}")
    
    if not health['repository_loaded']:
        print("\nWARNING: No repository loaded. Enhanced fallback will use basic fallback.")
        print("Run generate_fallback_repository.py first to create the repository.")
    
    # Test various weights and styles
    test_cases = [
        ("5 kg", "default"),
        ("10 pounds", "creative"),
        ("100 grams", "technical"),
        ("2.5 tons", "default"),
        ("1 ounce", "creative"),
        ("75 kg", "technical"),
        ("500 mg", "default"),
        ("1000 kg", "creative")
    ]
    
    print("\nTesting various weight comparisons:")
    print("-" * 50)
    
    for weight_input, style in test_cases:
        request = MVPComparisonRequest(
            weight_input=weight_input,
            style=style
        )
        
        try:
            response = await service.create_comparison(request)
            print(f"\nWeight: {weight_input} (Style: {style})")
            print(f"Processed: {response.weight_processed}")
            print(f"Comparison: {response.comparison_text}")
            print(f"Provider: {response.provider_used}")
            print(f"Response Time: {response.response_time_ms}ms")
        except Exception as e:
            print(f"\nERROR for {weight_input}: {e}")
    
    # Show repository statistics if available
    if health['repository_loaded']:
        stats = service.get_repository_stats()
        print("\n\nRepository Statistics:")
        print("-" * 50)
        print(f"Total Responses: {stats['total_responses']}")
        print("\nBy Style:")
        for style, count in stats['by_style'].items():
            print(f"  {style}: {count} responses")
        
        # Test rotation by requesting same weight multiple times
        print("\n\nTesting Response Rotation:")
        print("-" * 50)
        print("Requesting '50 kg' with default style 5 times:")
        
        seen_responses = set()
        for i in range(5):
            request = MVPComparisonRequest(
                weight_input="50 kg",
                style="default"
            )
            response = await service.create_comparison(request)
            comparison = response.comparison_text
            
            if comparison in seen_responses:
                print(f"  {i+1}. [REPEATED] {comparison[:60]}...")
            else:
                print(f"  {i+1}. [NEW] {comparison[:60]}...")
                seen_responses.add(comparison)
        
        print(f"\nUnique responses: {len(seen_responses)}/5")
    
    print("\n\nTest complete!")


if __name__ == "__main__":
    asyncio.run(test_enhanced_fallback())