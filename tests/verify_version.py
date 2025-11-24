import requests
import os
import sys

# Configuration
BASE_URL = "http://127.0.0.1:8000/api/v1/query"
API_KEY = "dev-api-key-123"  # Assuming this is in NT_QUERY_API_KEYS

def test_version_param():
    print("--- Testing Version Parameter ---")
    
    # Case 1: Package only
    print("\n1. Requesting package 'react' (no version)...")
    try:
        response = requests.get(
            BASE_URL,
            params={"package": "react"},
            headers={"X-API-Key": API_KEY}
        )
        print(f"Status Code: {response.status_code}")
        # We expect 200, 202, or 404 depending on DB state, but request should work
    except Exception as e:
        print(f"Request failed: {e}")

    # Case 2: Package + Version
    print("\n2. Requesting package 'react' with version '18.2.0'...")
    try:
        response = requests.get(
            BASE_URL,
            params={"package": "react", "version": "18.2.0"},
            headers={"X-API-Key": API_KEY}
        )
        print(f"Status Code: {response.status_code}")
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_version_param()
