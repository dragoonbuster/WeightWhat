#!/usr/bin/env python3
"""Test script for counter persistence"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.persistent_counter import PersistentCounter

async def test_counter():
    """Test counter functionality"""
    print("Testing counter persistence...")
    
    # Create counter instance
    counter = PersistentCounter()
    
    # Get current value
    current = await counter.get()
    print(f"Current counter value: {current}")
    
    # Test increment
    print("Testing increment...")
    new_value = await counter.increment()
    print(f"New value after increment: {new_value}")
    
    # Verify persistence by creating new instance
    print("\nTesting persistence with new instance...")
    counter2 = PersistentCounter()
    persisted_value = await counter2.get()
    print(f"Value from new instance: {persisted_value}")
    
    if persisted_value == new_value:
        print("✓ Counter persistence working correctly!")
    else:
        print("✗ Counter persistence FAILED!")
        return False
    
    # Show storage location
    print(f"\nCounter stored at: {counter.storage_path}")
    
    # Test concurrent increments
    print("\nTesting concurrent increments...")
    tasks = [counter.increment() for _ in range(5)]
    results = await asyncio.gather(*tasks)
    print(f"Results from 5 concurrent increments: {results}")
    
    final_value = await counter.get()
    print(f"Final counter value: {final_value}")
    
    expected = new_value + 5
    if final_value == expected:
        print("✓ Concurrent increments working correctly!")
    else:
        print(f"✗ Concurrent increments FAILED! Expected {expected}, got {final_value}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_counter())
    sys.exit(0 if success else 1)