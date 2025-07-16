#!/usr/bin/env python3
"""
Generate Comprehensive Fallback Response Repository

This script generates a large repository of AI-powered weight comparisons
organized by weight ranges and styles for use when AI providers are unavailable.
"""

import asyncio
import sys
import os
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path, override=True)
    print(f"Loaded environment from {env_path}")

# Add project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from src.services.fallback_response_generator import FallbackResponseGenerator


async def main():
    """Main function to generate fallback repository"""
    
    print("====================================================")
    print("    FALLBACK RESPONSE REPOSITORY GENERATOR")
    print("====================================================")
    print()
    
    # Check for API keys
    api_keys_found = []
    if os.getenv('SIZECOMPARATOR_OPENAI_API_KEY'):
        api_keys_found.append('OpenAI')
    if os.getenv('SIZECOMPARATOR_ANTHROPIC_API_KEY'):
        api_keys_found.append('Anthropic')
    if os.getenv('SIZECOMPARATOR_XAI_API_KEY'):
        api_keys_found.append('X.AI')
    
    if not api_keys_found:
        print("ERROR: No AI provider API keys found!")
        print("This script requires at least one AI provider to generate responses.")
        print("Please add API keys to your .env file:")
        print("  - SIZECOMPARATOR_OPENAI_API_KEY")
        print("  - SIZECOMPARATOR_ANTHROPIC_API_KEY")
        print("  - SIZECOMPARATOR_XAI_API_KEY")
        return
    
    print(f"Found API keys for: {', '.join(api_keys_found)}")
    print()
    
    # Check if repository already exists
    repository_file = Path("fallback_responses.json")
    if repository_file.exists():
        print(f"WARNING: Repository file already exists at {repository_file}")
        response = input("Do you want to overwrite it? (yes/no): ").strip().lower()
        if response != "yes":
            print("Aborting generation.")
            return
    
    # Create generator
    generator = FallbackResponseGenerator()
    
    # Get generation parameters
    print("\nGeneration Parameters:")
    print(f"  - Weight ranges: {len(generator.weight_ranges)}")
    print(f"  - Styles: {len(generator.styles)} ({', '.join(generator.styles)})")
    print(f"  - Responses per combination: {generator.responses_per_combination}")
    
    total_expected = len(generator.weight_ranges) * len(generator.styles) * generator.responses_per_combination
    print(f"  - Total responses to generate: {total_expected}")
    
    # Estimate time
    avg_response_time = 2.0  # seconds per response (conservative estimate)
    estimated_time = total_expected * avg_response_time
    print(f"\nEstimated generation time: {estimated_time / 60:.1f} minutes")
    
    # Confirm generation
    response = input("\nProceed with generation? (yes/no): ").strip().lower()
    if response != "yes":
        print("Aborting generation.")
        return
    
    print("\nStarting generation...")
    print("This may take a while. Feel free to grab a coffee!")
    print()
    
    try:
        # Generate repository
        results = await generator.generate_comprehensive_repository()
        
        print("\n====================================================")
        print("          GENERATION COMPLETE!")
        print("====================================================")
        print(f"Successfully generated: {results['total_generated']} responses")
        print(f"Failed generations: {results['total_failed']}")
        print(f"Repository saved to: {results['repository_file']}")
        
        # Show repository stats
        stats = generator.get_repository_stats()
        print("\nRepository Statistics:")
        print(f"  - Total responses: {stats['total_responses']}")
        print(f"  - Coverage: {stats['coverage']['percentage']:.1f}%")
        print("\n  By style:")
        for style, count in stats['by_style'].items():
            print(f"    - {style}: {count} responses")
        
    except KeyboardInterrupt:
        print("\n\nGeneration interrupted by user!")
        print("Partial results may have been saved.")
    except Exception as e:
        print(f"\nERROR during generation: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())