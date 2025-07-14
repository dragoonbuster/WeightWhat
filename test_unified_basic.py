#!/usr/bin/env python3
"""
Basic test of unified app functionality
"""

import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_basic_functionality():
    """Test basic unified app functionality"""
    
    try:
        print("🧪 Testing Unified App Basic Functionality")
        print("=" * 50)
        
        # Test imports
        from core.environment import EnvironmentManager
        from services.shared.service_factory import ServiceType, ComparisonServiceFactory
        from models.mvp import MVPComparisonRequest, MVPComparisonResponse
        
        print("1. ✅ Imports successful")
        
        # Test environment
        env_manager = EnvironmentManager()
        print(f"2. ✅ Environment: {env_manager.environment}")
        
        # Test service factory
        factory = ComparisonServiceFactory(env_manager)
        print(f"3. ✅ Service factory created")
        
        # Test service creation
        basic_service = factory.create_basic_service()
        print(f"4. ✅ Basic service: {type(basic_service).__name__}")
        
        # Test request creation
        request = MVPComparisonRequest(
            weight_input="5 kg",
            style="default",
            provider="auto"
        )
        print(f"5. ✅ Request created: {request.weight_input}")
        
        # Test service call
        print("6. 🧪 Testing service call...")
        result = await basic_service.create_comparison(request)
        print(f"   ✅ Response: {result.comparison_text[:50]}...")
        print(f"   ✅ Provider: {result.provider_used}")
        print(f"   ✅ Response time: {result.response_time_ms}ms")
        
        print("\n" + "=" * 50)
        print("🎉 Basic functionality test passed!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def async_test():
    """Run async test"""
    return await test_basic_functionality()


if __name__ == "__main__":
    import asyncio
    
    try:
        success = asyncio.run(async_test())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Failed to run test: {e}")
        sys.exit(1)