import asyncio
import httpx
from tenacity import AsyncRetrying
from common_lib.retry_config import get_retry_strategy, _is_retryable_exception

async def test_retry_logic():
    print("--- Testing Retry Logic ---")
    
    # Mock function that fails twice then succeeds
    call_count = 0
    
    async def flaky_api_call():
        nonlocal call_count
        call_count += 1
        print(f"Attempt {call_count}...")
        if call_count < 3:
            # Simulate 500 error (retryable)
            raise httpx.HTTPStatusError(
                "Server Error", 
                request=httpx.Request("GET", "http://test"), 
                response=httpx.Response(500)
            )
        return "Success"

    print("\n1. Testing Retryable Exception (500 Error)")
    retry_strategy = AsyncRetrying(**get_retry_strategy())
    
    try:
        async for attempt in retry_strategy:
            with attempt:
                result = await flaky_api_call()
                print(f"Result: {result}")
    except Exception as e:
        print(f"Failed: {e}")

    if call_count == 3:
        print("PASS: Retried 3 times and succeeded.")
    else:
        print(f"FAIL: Expected 3 attempts, got {call_count}")

    # Reset
    call_count = 0
    
    async def fatal_api_call():
        nonlocal call_count
        call_count += 1
        print(f"Attempt {call_count}...")
        # Simulate 400 error (non-retryable)
        raise httpx.HTTPStatusError(
            "Bad Request", 
            request=httpx.Request("GET", "http://test"), 
            response=httpx.Response(400)
        )

    print("\n2. Testing Non-Retryable Exception (400 Error)")
    try:
        async for attempt in retry_strategy:
            with attempt:
                await fatal_api_call()
    except httpx.HTTPStatusError:
        print("Caught expected HTTPStatusError")
    except Exception as e:
        print(f"Caught unexpected exception: {type(e)}")

    if call_count == 1:
        print("PASS: Stopped after 1 attempt.")
    else:
        print(f"FAIL: Expected 1 attempt, got {call_count}")

if __name__ == "__main__":
    asyncio.run(test_retry_logic())
