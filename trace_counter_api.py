#!/usr/bin/env python3
"""Trace the counter behavior through API calls with detailed logging"""

import asyncio
import logging
import sys
from pathlib import Path

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

async def trace_counter_behavior():
    """Trace counter behavior with detailed logging"""
    
    print("\nTracing Counter Behavior\n" + "="*60)
    
    # Import after logging is setup
    from src.services.persistent_counter import PersistentCounter, get_persistent_counter
    
    # Test 1: Direct counter access
    print("\n1. Direct Counter Access:")
    counter = get_persistent_counter()
    value1 = await counter.get()
    print(f"   Initial value: {value1}")
    
    # Test 2: Increment
    print("\n2. Increment Test:")
    new_val = await counter.increment()
    print(f"   New value after increment: {new_val}")
    
    # Test 3: Create app and check counter
    print("\n3. App Context Test:")
    from src.api.unified_app import UnifiedSizeComparatorApp
    from src.core.environment import EnvironmentManager
    
    env_manager = EnvironmentManager()
    app_instance = UnifiedSizeComparatorApp(env_manager)
    
    # Check if it's the same counter
    print(f"   App counter is same instance: {app_instance.counter is counter}")
    
    # Get value through app's counter
    app_value = await app_instance.counter.get()
    print(f"   Value through app counter: {app_value}")
    
    # Test 4: Simulate API endpoint behavior
    print("\n4. Simulating API Endpoint:")
    try:
        counter_value = await app_instance.counter.get()
        result = {
            "count": counter_value,
            "timestamp": "2025-07-18T00:00:00"
        }
        print(f"   API would return: {result}")
    except Exception as e:
        print(f"   Error in API simulation: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 5: Check file contents
    print("\n5. File Check:")
    counter_file = Path.home() / ".weightwhat" / "counter.json"
    if counter_file.exists():
        print(f"   File contents: {counter_file.read_text().strip()}")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    asyncio.run(trace_counter_behavior())