#!/usr/bin/env python3
"""Test counter path resolution and permissions"""

import os
from pathlib import Path

print("Testing Counter Path Resolution")
print("="*60)

# Check all possible paths
possible_paths = [
    Path("/var/lib/weightwhat/counter.json"),
    Path("/opt/WeightWhat/data/counter.json"),
    Path.home() / ".weightwhat" / "counter.json",
    Path("/tmp/sizecomparator_counter.json")
]

print("Checking paths in order of preference:")
for i, path in enumerate(possible_paths, 1):
    print(f"\n{i}. {path}")
    print(f"   Parent exists: {path.parent.exists()}")
    print(f"   Parent writable: {os.access(path.parent, os.W_OK) if path.parent.exists() else 'N/A'}")
    print(f"   File exists: {path.exists()}")
    if path.exists():
        try:
            content = path.read_text()
            print(f"   Content: {content.strip()}")
        except Exception as e:
            print(f"   Read error: {e}")

# Test write permissions
print("\n" + "-"*60)
print("Testing write permissions:")

test_dir = Path.home() / ".weightwhat"
test_file = test_dir / "test_write.tmp"

try:
    test_dir.mkdir(exist_ok=True)
    test_file.write_text("test")
    print(f"✓ Can write to {test_dir}")
    test_file.unlink()
except Exception as e:
    print(f"✗ Cannot write to {test_dir}: {e}")

# Check environment
print("\n" + "-"*60)
print("Environment info:")
print(f"User: {os.getenv('USER', 'unknown')}")
print(f"Home: {Path.home()}")
print(f"CWD: {os.getcwd()}")
print(f"Running as UID: {os.getuid()}")

# Import and test the actual counter logic
print("\n" + "-"*60)
print("Testing actual PersistentCounter path selection:")

import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.services.persistent_counter import PersistentCounter

# Create instance
counter = PersistentCounter()
print(f"Selected path: {counter.storage_path}")
print(f"Path exists: {counter.storage_path.exists()}")
if counter.storage_path.exists():
    print(f"Content: {counter.storage_path.read_text().strip()}")