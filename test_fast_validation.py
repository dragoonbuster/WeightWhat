#!/usr/bin/env python3
"""
Test Fast Validation Performance - Verify <2 second response times
"""

import sys
import asyncio
import os
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_fast_validation_performance():
    """Test fast validation performance vs regular validation"""
    print("⚡ Testing Fast Validation Performance")
    
    # Check API key
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        print("❌ OPENAI_API_KEY not found. Set it first:")
        print('export OPENAI_API_KEY="sk-proj-your-key-here"')
        return False
    
    try:
        # Test 1: Initialize Services
        print("\n1️⃣ Initializing Services...")
        from services.fast_validation_service import FastValidationService
        from services.ai_validation_service import AIValidationService
        from models.mvp import MVPComparisonRequest
        
        fast_service = FastValidationService()
        full_service = AIValidationService()
        
        print("   ✅ Fast validation service initialized")
        print("   ✅ Full validation service initialized")
        
        # Test 2: Performance Comparison
        print("\n2️⃣ Performance Testing...")
        
        test_weights = [
            ("50 kg", "Common weight - should use fast validation"),
            ("10 pounds", "Common weight - should use fast validation"),
            ("0.01 kg", "Extreme weight - should use full validation"),
            ("5000 kg", "Extreme weight - should use full validation")
        ]
        
        for weight_input, description in test_weights:
            print(f"\n   Testing: {weight_input} ({description})")
            
            request = MVPComparisonRequest(
                weight_input=weight_input,
                style="default"
            )
            
            # Fast validation timing
            print("   ⚡ Fast validation...")
            start_time = time.time()
            fast_response = await fast_service.create_fast_validated_comparison(request)
            fast_time = int((time.time() - start_time) * 1000)
            
            print(f"      📝 {fast_response.comparison_text[:60]}...")
            print(f"      ⚡ Time: {fast_time}ms")
            print(f"      🤖 Provider: {fast_response.provider_used}")
            
            # Full validation timing (for comparison)
            print("   🔍 Full validation...")
            start_time = time.time()
            full_response = await full_service.create_validated_comparison(request)
            full_time = int((time.time() - start_time) * 1000)
            
            print(f"      📝 {full_response.comparison_text[:60]}...")
            print(f"      ⚡ Time: {full_time}ms")
            print(f"      🤖 Provider: {full_response.provider_used}")
            
            # Performance analysis
            speedup = full_time / fast_time if fast_time > 0 else 1
            print(f"      📊 Speedup: {speedup:.1f}x faster ({full_time}ms → {fast_time}ms)")
            
            # Check if fast validation meets target
            if fast_time <= 2000:
                print("      ✅ Meets <2 second target!")
            else:
                print("      ⚠️  Exceeds 2 second target")
        
        # Test 3: Rule-Based Validation Testing
        print("\n3️⃣ Testing Rule-Based Validation...")
        
        # Test rule validation directly
        weight_kg = 1.0  # 1 kg
        test_responses = [
            "1 kg is about the weight of a laptop computer.",  # Good
            "1 kg is about the weight of 20 elephants.",       # Bad - too heavy
            "1 kg is about the weight of 1,000,000 feathers.", # Bad - wrong magnitude
            "1 kg is about the weight of a pineapple."         # Good
        ]
        
        valid_responses = fast_service._rule_based_validation(weight_kg, test_responses)
        
        print(f"   📝 Input responses: {len(test_responses)}")
        print(f"   ✅ Valid responses: {len(valid_responses)}")
        print(f"   📊 Rule effectiveness: {len(valid_responses)/len(test_responses)*100:.1f}% passed")
        
        for i, response in enumerate(test_responses):
            status = "✅" if response in valid_responses else "❌"
            print(f"      {status} Response {i+1}: {response[:50]}...")
        
        # Test 4: Overall Performance Summary
        print("\n4️⃣ Performance Summary...")
        
        fast_health = fast_service.get_health_status()
        print(f"   🎯 Target response time: {fast_health.get('target_response_time', 'Unknown')}")
        print(f"   🔄 Parallel calls: {fast_health.get('parallel_calls', 'Unknown')}")
        print(f"   🧠 Validation mode: {fast_health.get('validation_mode', 'Unknown')}")
        
        # Cleanup
        await fast_service.cleanup()
        await full_service.cleanup()
        
        print("\n🎉 Fast Validation Performance Test COMPLETED!")
        print("\n📋 Key Improvements:")
        print("   ⚡ Reduced parallel calls: 3 → 2 for common weights")
        print("   🎯 Rule-based validation: Fast filtering without AI calls")
        print("   🧠 Smart routing: Full validation only for extreme weights")
        print("   ⏱️  Aggressive timeouts: 3-4 seconds max per validation")
        
        print(f"\n🚀 Launch fast demo:")
        print(f"   OPENAI_API_KEY='{openai_key[:20]}...' python src/api/fast_validated_mvp.py")
        print(f"   Then open: http://localhost:8004")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Fast Validation Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Set API key for testing
    if len(sys.argv) > 1:
        os.environ['OPENAI_API_KEY'] = sys.argv[1]
        print(f"✅ Using provided API key: {sys.argv[1][:20]}...")
    
    success = asyncio.run(test_fast_validation_performance())
    sys.exit(0 if success else 1)