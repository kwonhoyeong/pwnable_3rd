import asyncio
import httpx
import sys

BASE_URL = "http://127.0.0.1:8000"
API_KEY = "dev-api-key-123"

async def test_auth():
    print("--- Testing Authentication ---")
    async with httpx.AsyncClient() as client:
        # 1. No API Key
        resp = await client.get(f"{BASE_URL}/api/v1/stats")
        print(f"No API Key: {resp.status_code} (Expected 403/401)")
        
        # 2. Invalid API Key
        resp = await client.get(f"{BASE_URL}/api/v1/stats", headers={"X-API-Key": "invalid"})
        print(f"Invalid API Key: {resp.status_code} (Expected 403)")

        # 3. Valid API Key (Health check might be public or protected depending on implementation, let's check a protected one)
        # Actually /health is public in the code I saw? No, wait. 
        # Let's check /api/v1/stats which is definitely protected.
        resp = await client.get(f"{BASE_URL}/api/v1/stats", headers={"X-API-Key": API_KEY})
        print(f"Valid API Key (/stats): {resp.status_code} (Expected 200)")

async def test_rate_limit():
    print("\n--- Testing Rate Limiting ---")
    async with httpx.AsyncClient() as client:
        # Send 6 requests to /api/v1/stats (Limit is 5/minute)
        for i in range(1, 8):
            resp = await client.get(f"{BASE_URL}/api/v1/stats", headers={"X-API-Key": API_KEY})
            print(f"Request {i}: {resp.status_code}")
            if resp.status_code == 429:
                print("Rate limit hit successfully!")
                return
    print("Rate limit NOT hit (Failed)")

if __name__ == "__main__":
    async def main():
        await test_auth()
        await test_rate_limit()

    asyncio.run(main())
