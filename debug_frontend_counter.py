#!/usr/bin/env python3
"""Debug script to simulate browser loading the counter"""

import requests
import time

def test_frontend_counter():
    print("=== Testing Frontend Counter Flow ===\n")
    
    # Step 1: Load main page
    print("1. Loading main page...")
    response = requests.get("http://localhost:8000/")
    print(f"   Status: {response.status_code}")
    print(f"   Counter element found: {'<span id=\"counter\">' in response.text}")
    
    # Step 2: Load JavaScript files
    print("\n2. Loading JavaScript files...")
    js_files = [
        "/js/api-client.js?v=3",
        "/js/app.js?v=4"
    ]
    
    for js_file in js_files:
        response = requests.get(f"http://localhost:8000{js_file}")
        print(f"   {js_file}: {response.status_code} ({len(response.text)} bytes)")
    
    # Step 3: Simulate API call
    print("\n3. Simulating counter API call...")
    response = requests.get("http://localhost:8000/api/counter")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   Response: {data}")
        print(f"   Counter value: {data.get('count', 'NOT FOUND')}")
    
    # Step 4: Test with different Accept headers
    print("\n4. Testing with different headers...")
    headers_to_test = [
        {"Accept": "application/json"},
        {"Accept": "*/*"},
        {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
    ]
    
    for headers in headers_to_test:
        response = requests.get("http://localhost:8000/api/counter", headers=headers)
        print(f"   Headers {headers}: Status {response.status_code}")
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"     Counter: {data.get('count', 'NOT FOUND')}")
            except:
                print(f"     Response: {response.text[:100]}")
    
    # Step 5: Test multiple rapid calls
    print("\n5. Testing multiple rapid calls...")
    for i in range(3):
        response = requests.get("http://localhost:8000/api/counter")
        if response.status_code == 200:
            data = response.json()
            print(f"   Call {i+1}: count = {data.get('count', 'NOT FOUND')}")
        time.sleep(0.1)

if __name__ == "__main__":
    test_frontend_counter()