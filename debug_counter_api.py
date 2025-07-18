#!/usr/bin/env python3
"""Debug script to trace counter API issues"""

import asyncio
import sys
import os
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.persistent_counter import PersistentCounter, get_persistent_counter


async def test_counter_directly():
    """Test the counter directly without going through the API"""
    print("=== Testing Counter Directly ===")
    
    # Test 1: Create a new instance (not using global)
    print("\n1. Testing new PersistentCounter instance:")
    counter1 = PersistentCounter()
    value1 = await counter1.get()
    print(f"   Counter value: {value1}")
    print(f"   Storage path: {counter1.storage_path}")
    
    # Test 2: Use the global instance
    print("\n2. Testing global counter instance:")
    counter2 = get_persistent_counter()
    value2 = await counter2.get()
    print(f"   Counter value: {value2}")
    print(f"   Storage path: {counter2.storage_path}")
    print(f"   Same instance as counter1? {counter1 is counter2}")
    
    # Test 3: Create another global instance
    print("\n3. Testing another call to get_persistent_counter:")
    counter3 = get_persistent_counter()
    value3 = await counter3.get()
    print(f"   Counter value: {value3}")
    print(f"   Same instance as counter2? {counter2 is counter3}")
    
    # Test 4: Check what's in the file
    print("\n4. Checking counter files directly:")
    possible_paths = [
        Path("/var/lib/weightwhat/counter.json"),
        Path("/opt/WeightWhat/data/counter.json"),
        Path.home() / ".weightwhat" / "counter.json",
        Path("/tmp/sizecomparator_counter.json")
    ]
    
    for path in possible_paths:
        if path.exists():
            try:
                import json
                data = json.loads(path.read_text())
                print(f"   {path}: {data}")
            except Exception as e:
                print(f"   {path}: Error reading - {e}")
        else:
            print(f"   {path}: Does not exist")


async def test_api_flow():
    """Test how the API initializes the counter"""
    print("\n\n=== Testing API Flow ===")
    
    from src.api.unified_app import UnifiedSizeComparatorApp
    from src.core.environment import EnvironmentManager
    
    # Create app instance
    print("\n1. Creating UnifiedSizeComparatorApp instance:")
    env_manager = EnvironmentManager()
    app_instance = UnifiedSizeComparatorApp(env_manager)
    
    # Check the counter
    print(f"   App counter instance: {app_instance.counter}")
    print(f"   App counter storage path: {app_instance.counter.storage_path}")
    value = await app_instance.counter.get()
    print(f"   Counter value from app: {value}")
    
    # Check if it's the same as global
    global_counter = get_persistent_counter()
    print(f"   Same as global counter? {app_instance.counter is global_counter}")
    
    # Test the counter endpoint directly
    print("\n2. Testing counter endpoint logic:")
    try:
        counter_value = await app_instance.counter.get()
        result = {
            "count": counter_value,
            "timestamp": "test"
        }
        print(f"   Endpoint would return: {result}")
    except Exception as e:
        print(f"   Error in endpoint logic: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests"""
    await test_counter_directly()
    await test_api_flow()


if __name__ == "__main__":
    asyncio.run(main())