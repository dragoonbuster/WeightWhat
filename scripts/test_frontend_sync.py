#!/usr/bin/env python3
"""Test frontend counter sync with backend"""

import asyncio
import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.persistent_counter import PersistentCounter

async def test_frontend_sync():
    """Test that frontend sync pattern works correctly"""
    print("Testing frontend/backend counter sync pattern...")
    
    counter = PersistentCounter()
    
    # Simulate frontend behavior:
    # 1. Frontend loads initial counter
    initial_value = await counter.get()
    print(f"1. Frontend loads counter: {initial_value}")
    
    # 2. User performs action, frontend optimistically increments local display
    frontend_display = initial_value + 1
    print(f"2. Frontend optimistically shows: {frontend_display}")
    
    # 3. Backend receives API call and increments
    backend_new_value = await counter.increment()
    print(f"3. Backend increments to: {backend_new_value}")
    
    # 4. Frontend reloads after 1 second
    await asyncio.sleep(1)
    reloaded_value = await counter.get()
    print(f"4. Frontend reloads and gets: {reloaded_value}")
    
    # Verify sync
    if frontend_display == backend_new_value == reloaded_value:
        print("\n✓ Frontend/backend sync working correctly!")
        print("  - Frontend optimistic update matches backend")
        print("  - Reload confirms correct value")
    else:
        print("\n✗ Sync issue detected!")
        print(f"  - Frontend showed: {frontend_display}")
        print(f"  - Backend incremented to: {backend_new_value}")
        print(f"  - Reload returned: {reloaded_value}")
        return False
    
    # Test race condition scenario
    print("\nTesting race condition (multiple users)...")
    
    # Current state
    start_value = await counter.get()
    print(f"Starting value: {start_value}")
    
    # Simulate 3 users clicking at the same time
    async def simulate_user(user_id):
        # Each user loads current value
        loaded = await counter.get()
        # Shows optimistic increment
        optimistic = loaded + 1
        # Backend increments
        actual = await counter.increment()
        return {
            "user": user_id,
            "loaded": loaded,
            "optimistic": optimistic,
            "actual": actual
        }
    
    # Run concurrent users
    results = await asyncio.gather(
        simulate_user(1),
        simulate_user(2),
        simulate_user(3)
    )
    
    print("\nUser simulation results:")
    for r in results:
        print(f"  User {r['user']}: loaded={r['loaded']}, showed={r['optimistic']}, actual={r['actual']}")
    
    final_value = await counter.get()
    expected_final = start_value + 3
    
    if final_value == expected_final:
        print(f"\n✓ Race condition handled correctly!")
        print(f"  - Started at: {start_value}")
        print(f"  - Expected after 3 increments: {expected_final}")
        print(f"  - Actual final value: {final_value}")
    else:
        print(f"\n✗ Race condition issue!")
        print(f"  - Expected: {expected_final}, Got: {final_value}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_frontend_sync())
    sys.exit(0 if success else 1)