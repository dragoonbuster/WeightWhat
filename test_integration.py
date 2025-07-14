#!/usr/bin/env python3
"""
Quick integration test for SizeComparator core components
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_core_integration():
    """Test core component integration"""
    print("🧪 Starting SizeComparator Integration Test")
    
    try:
        # Test 1: Weight Processing
        print("\n1️⃣ Testing Weight Processing...")
        from services.weight_processor import WeightProcessor
        from core.environment import EnvironmentManager
        
        # Initialize environment
        env_manager = EnvironmentManager()
        processor = WeightProcessor()
        
        # Test weight parsing
        result = processor.process_weight("5.5 kilograms")
        print(f"   ✅ Processed '5.5 kilograms' -> {result.weight_kg} kg")
        
        # Test 2: Models and Validation
        print("\n2️⃣ Testing Data Models...")
        from models.requests import WeightComparisonRequest
        from models.weight import WeightInput
        
        request = WeightComparisonRequest(
            weight_input="10 pounds",
            comparison_style="default",
            include_visualization=True
        )
        print(f"   ✅ Created request: {request.weight_input}")
        
        # Test 3: Cache Service (Memory fallback)
        print("\n3️⃣ Testing Cache Service...")
        from services.cache import CacheService
        
        cache = CacheService.create_memory_cache()
        await cache.set("test_key", "test_value", ttl=60)
        value = await cache.get("test_key")
        print(f"   ✅ Cache set/get: {value}")
        
        # Test 4: Error Monitoring
        print("\n4️⃣ Testing Error Monitoring...")
        from core.monitoring import StructuredLogger, ServiceName
        
        logger = StructuredLogger(ServiceName.API_GATEWAY)
        logger.info("Integration test log entry", test_component="integration")
        print("   ✅ Structured logging works")
        
        # Test 5: Configuration Loading
        print("\n5️⃣ Testing Configuration...")
        from core.config import ConfigLoader
        
        config_loader = ConfigLoader()
        config = config_loader.load_configuration()
        print(f"   ✅ Config loaded with {len(config)} sections")
        
        print("\n🎉 Integration Test PASSED! All core components working.")
        return True
        
    except Exception as e:
        print(f"\n❌ Integration Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_core_integration())
    sys.exit(0 if success else 1)