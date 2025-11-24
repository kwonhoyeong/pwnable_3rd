import asyncio
import json
import os
import redis.asyncio as redis

REDIS_URL = os.getenv("NT_REDIS_URL", "redis://localhost:6379/0")
ANALYSIS_QUEUE_KEY = "analysis_tasks"

async def push_task():
    r = redis.from_url(REDIS_URL, decode_responses=True)
    task = {
        "package": "express",
        "version": "latest",
        "force": True
    }
    await r.rpush(ANALYSIS_QUEUE_KEY, json.dumps(task))
    print(f"Pushed task: {task}")
    await r.close()

if __name__ == "__main__":
    asyncio.run(push_task())
