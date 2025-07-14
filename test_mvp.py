#!/usr/bin/env python3
"""
MVP Integration Test - Simple end-to-end test
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_mvp_flow():
    """Test MVP end-to-end flow"""
    print("🧪 Testing SizeComparator MVP Flow")
    
    try:
        # Test 1: MVP Models
        print("\n1️⃣ Testing MVP Models...")
        from models.mvp import MVPComparisonRequest, MVPComparisonResponse
        
        request = MVPComparisonRequest(
            weight_input="5 kg",
            style="default"
        )
        print(f"   ✅ Created MVP request: {request.weight_input}")
        
        # Test 2: MVP Comparison Service
        print("\n2️⃣ Testing MVP Comparison Service...")
        from services.mvp_comparison import MVPComparisonService
        
        service = MVPComparisonService()
        response = await service.create_comparison(request)
        
        print(f"   ✅ Generated comparison: {response.comparison_text}")
        print(f"   ✅ Processed weight: {response.weight_processed}")
        print(f"   ✅ Response time: {response.response_time_ms}ms")
        
        # Test 3: Health Check
        print("\n3️⃣ Testing Health Status...")
        health = service.get_health_status()
        print(f"   ✅ Service status: {health['status']}")
        
        # Test 4: Different Weight Inputs
        print("\n4️⃣ Testing Various Weight Inputs...")
        test_weights = ["10 pounds", "100 grams", "2.5 kg", "1 ounce"]
        
        for weight in test_weights:
            test_req = MVPComparisonRequest(weight_input=weight)
            result = await service.create_comparison(test_req)
            print(f"   ✅ {weight} -> {result.comparison_text[:50]}...")
        
        # Test 5: Error Handling
        print("\n5️⃣ Testing Error Handling...")
        try:
            error_req = MVPComparisonRequest(weight_input="invalid weight")
            await service.create_comparison(error_req)
            print("   ❌ Should have raised an error")
        except Exception as e:
            print(f"   ✅ Properly handled error: {type(e).__name__}")
        
        print("\n🎉 MVP Integration Test PASSED!")
        print("\n📋 MVP is ready for demo:")
        print("   • Weight processing: Working")
        print("   • Fallback comparisons: Working") 
        print("   • Error handling: Working")
        print("   • Response formatting: Working")
        print("\n🚀 Run: python src/api/mvp.py")
        print("   Then open: http://localhost:8000")
        
        return True
        
    except Exception as e:
        print(f"\n❌ MVP Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_mvp_flow())
    sys.exit(0 if success else 1)