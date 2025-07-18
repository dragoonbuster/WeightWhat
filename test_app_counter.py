#!/usr/bin/env python3
"""Test how the counter behaves in the app context"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

print("Testing counter in app context...")

# Import the way the app does it
from src.services.persistent_counter import get_persistent_counter

# Get counter 1
counter1 = get_persistent_counter()
print(f"Counter 1 instance: {id(counter1)}")
print(f"Counter 1 storage path: {counter1.storage_path}")

# Get counter 2 (should be same instance)
counter2 = get_persistent_counter()
print(f"Counter 2 instance: {id(counter2)}")
print(f"Same instance? {counter1 is counter2}")

# Now test what happens when we import unified_app
print("\nImporting unified_app...")
from src.api.unified_app import UnifiedSizeComparatorApp
from src.core.environment import EnvironmentManager

# Create app instance
env_manager = EnvironmentManager()
app_instance = UnifiedSizeComparatorApp(env_manager)
print(f"App counter instance: {id(app_instance.counter)}")
print(f"Same as global? {app_instance.counter is counter1}")

# Create another app instance
app_instance2 = UnifiedSizeComparatorApp(env_manager)
print(f"App2 counter instance: {id(app_instance2.counter)}")
print(f"Same counter? {app_instance.counter is app_instance2.counter}")

# Check the global state
print("\nChecking global state...")
import src.services.persistent_counter as pc_module
print(f"Global _counter_instance: {pc_module._counter_instance}")
print(f"Is it the same? {pc_module._counter_instance is counter1}")