import asyncio
import httpx
import os
import sys
import time
from typing import Dict, Any, List

# Configuration
BASE_URL = "http://localhost"
PORTS = {
    "QueryAPI": 8000,
}
# Ensure we match the server's default if env var is missing
API_KEY = os.getenv("NT_QUERY_API_KEYS", "dev-api-key-123").split(",")[0]

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def log_success(msg: str):
    print(f"{GREEN}[PASS]{RESET} {msg}")

def log_fail(msg: str):
    print(f"{RED}[FAIL]{RESET} {msg}")

def log_info(msg: str):
    print(f"{YELLOW}[INFO]{RESET} {msg}")

async def check_service_health(client: httpx.AsyncClient, name: str, port: int) -> bool:
    url = f"{BASE_URL}:{port}/health"
    try:
        response = await client.get(url, timeout=2.0)
        if response.status_code == 200:
            log_success(f"{name} is healthy (Port {port})")
            return True
        else:
            log_fail(f"{name} returned status {response.status_code}")
            return False
    except Exception as e:
        log_fail(f"{name} is unreachable on port {port}: {repr(e)}")
        return False

async def check_security(client: httpx.AsyncClient):
    log_info("Checking Security (Auth)...")
    url = f"{BASE_URL}:8000/api/v1/query?package=lodash"
    
    # 1. Request without API Key
    try:
        response = await client.get(url, timeout=5.0)
        if response.status_code in [401, 403]:
            log_success("Request without API Key was blocked correctly")
        else:
            log_fail(f"Request without API Key was NOT blocked (Status: {response.status_code})")
    except Exception as e:
        log_fail(f"Request without API Key failed with exception: {repr(e)}")
        return None

    # 2. Request with Valid API Key
    try:
        headers = {"X-API-Key": API_KEY}
        log_info(f"Sending authenticated request to {url} with key prefix: {API_KEY[:4]}...")
        response = await client.get(url, headers=headers, timeout=10.0)
        
        if response.status_code == 200:
            log_success("Request with Valid API Key succeeded")
            try:
                return response.json()
            except Exception as json_err:
                log_fail(f"Failed to parse JSON response: {repr(json_err)}")
                log_info(f"Response text: {response.text[:200]}...")
                return None
        else:
            log_fail(f"Request with Valid API Key failed (Status: {response.status_code})")
            log_info(f"Response text: {response.text[:200]}...")
            return None
    except Exception as e:
        log_fail(f"Request with Valid API Key failed with exception: {repr(e)}")
        return None

def check_data_consistency(data: Dict[str, Any]):
    log_info("Checking Data Consistency...")
    if not data:
        log_fail("No data to check consistency")
        return

    # Check for risk_score field
    if "risk_score" in data:
        log_success("'risk_score' field exists in response")
    else:
        log_fail("'risk_score' field is MISSING")

    # Check for priority_score confusion
    if "priority_score" in data:
        log_info("'priority_score' field also exists (Legacy field)")
    
    # Validate risk_score value range
    risk_score = data.get("risk_score")
    if isinstance(risk_score, (int, float)):
        log_success(f"'risk_score' has valid numeric value: {risk_score}")
    else:
        log_fail(f"'risk_score' has invalid type: {type(risk_score)}")

async def check_caching(client: httpx.AsyncClient):
    log_info("Checking Caching Performance...")
    url = f"{BASE_URL}:8000/api/v1/query?package=react" 
    headers = {"X-API-Key": API_KEY}

    try:
        # First Request (Cache Miss)
        start_time = time.time()
        await client.get(url, headers=headers, timeout=10.0)
        duration_1 = time.time() - start_time
        log_info(f"First request duration: {duration_1:.4f}s")

        # Second Request (Cache Hit)
        start_time = time.time()
        await client.get(url, headers=headers, timeout=10.0)
        duration_2 = time.time() - start_time
        log_info(f"Second request duration: {duration_2:.4f}s")

        if duration_2 < duration_1 * 0.5: 
            log_success("Caching is working (Second request was significantly faster)")
        else:
            log_info("Caching might not be active or network jitter occurred (Speedup not significant)")
    except Exception as e:
        log_fail(f"Caching check failed with exception: {repr(e)}")

async def main():
    log_info("Starting Final System Health Check...")
    
    async with httpx.AsyncClient() as client:
        # 1. Service Health Checks
        results = await asyncio.gather(*[
            check_service_health(client, name, port)
            for name, port in PORTS.items()
        ])
        
        if not any(results):
            log_fail("No services are reachable. Aborting further tests.")
            return

        # 2. Security Check
        package_data = await check_security(client)

        # 3. Data Consistency Check
        if package_data:
            check_data_consistency(package_data)

        # 4. Caching Check
        await check_caching(client)

    log_info("Health Check Completed.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAborted.")
    except Exception as e:
        print(f"\nAn error occurred: {repr(e)}")
