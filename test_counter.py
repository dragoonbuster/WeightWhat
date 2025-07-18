#!/usr/bin/env python3
"""Test script to debug the counter persistence issue"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.persistent_counter import PersistentCounter

async def test_counter():
    print("Testing Counter Persistence\n" + "="*50)
    
    # Create a counter instance
    counter = PersistentCounter()
    print(f"Counter storage path: {counter.storage_path}")
    print(f"Storage path exists: {counter.storage_path.exists()}")
    
    # Get current value
    current = await counter.get()
    print(f"\nCurrent counter value: {current}")
    
    # Increment
    new_value = await counter.increment()
    print(f"After increment: {new_value}")
    
    # Get again
    verify = await counter.get()
    print(f"Verification read: {verify}")
    
    # Check file contents
    if counter.storage_path.exists():
        print(f"\nFile contents: {counter.storage_path.read_text()}")
    
    # Test with a new instance (simulates server restart)
    print("\n" + "-"*50)
    print("Creating new counter instance (simulating restart)...")
    counter2 = PersistentCounter()
    value2 = await counter2.get()
    print(f"New instance value: {value2}")
    
    # Test the global singleton
    print("\n" + "-"*50)
    print("Testing global singleton...")
    from src.services.persistent_counter import get_persistent_counter
    global_counter1 = get_persistent_counter()
    global_counter2 = get_persistent_counter()
    print(f"Same instance? {global_counter1 is global_counter2}")
    
    value_g1 = await global_counter1.get()
    print(f"Global counter value: {value_g1}")

if __name__ == "__main__":
    asyncio.run(test_counter())