#!/usr/bin/env python3
"""Debug script to understand the counter reset issue"""

import asyncio
import requests
import time
from pathlib import Path

async def debug_counter_flow():
    """Simulate the exact flow when page loads and makes API calls"""
    
    print("Debugging Counter Reset Issue")
    print("="*60)
    
    # Check current file value
    counter_file = Path.home() / ".weightwhat" / "counter.json"
    if counter_file.exists():
        print(f"Current file contents: {counter_file.read_text()}")
    
    # Make API call to get counter
    print("\n1. Making GET request to /api/counter...")
    try:
        response = requests.get("http://localhost:8000/api/counter")
        print(f"   Status: {response.status_code}")
        if response.ok:
            data = response.json()
            print(f"   Response: {data}")
            print(f"   Counter value: {data.get('count', 'N/A')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Wait a moment
    time.sleep(1)
    
    # Make a comparison request
    print("\n2. Making POST request to /api/compare...")
    try:
        payload = {
            "weight_input": "50 kg",
            "style": "default"
        }
        response = requests.post(
            "http://localhost:8000/api/compare?service_mode=basic",
            json=payload
        )
        print(f"   Status: {response.status_code}")
        if response.ok:
            print("   Comparison successful")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Check counter again
    print("\n3. Checking counter again...")
    try:
        response = requests.get("http://localhost:8000/api/counter")
        print(f"   Status: {response.status_code}")
        if response.ok:
            data = response.json()
            print(f"   Response: {data}")
            print(f"   Counter value: {data.get('count', 'N/A')}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Check file again
    print(f"\n4. File contents after: {counter_file.read_text()}")
    
    print("\n" + "="*60)
    print("ANALYSIS:")
    print("- If counter resets to 0, it's a persistence issue")
    print("- If counter doesn't increment, it's an increment issue")
    print("- If file doesn't update, it's a file I/O issue")

if __name__ == "__main__":
    # First ensure server is not running
    print("Make sure the server is running on port 8000")
    print("Run: python run_unified_server.py")
    input("Press Enter when ready...")
    
    asyncio.run(debug_counter_flow())