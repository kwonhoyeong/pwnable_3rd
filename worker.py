import asyncio
import json
import os
import signal
import sys
import traceback

import redis.asyncio as redis
from agent_orchestrator import AgentOrchestrator
from common_lib.logger import get_logger

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = get_logger("worker")

# Configuration
REDIS_URL = os.getenv("NT_REDIS_URL", "redis://localhost:6379/0")
ANALYSIS_QUEUE_KEY = "analysis_tasks"

async def process_task(orchestrator: AgentOrchestrator, task_json: str):
    try:
        task = json.loads(task_json)
        package = task.get("package")
        version = task.get("version", "latest")
        force = task.get("force", False)
        
        if not package:
            logger.warning("Invalid task received: missing package")
            return

        logger.info(f"🚀 Processing task for {package}@{version}")
        
        # Define progress callback
        def progress_cb(step: str, message: str):
            logger.info(f"[{step}] {message}")

        # Execute pipeline
        await orchestrator.orchestrate_pipeline(
            package=package,
            version_range=version,
            skip_threat_agent=False,
            force=force,
            progress_cb=progress_cb,
            ecosystem="npm"
        )
        logger.info(f"✅ Task completed for {package}")

    except json.JSONDecodeError:
        logger.error(f"Failed to decode task JSON: {task_json}")
    except Exception as e:
        logger.error(f"❌ Error processing task: {e}")
        traceback.print_exc()

async def worker():
    logger.info(f"🔧 Starting worker, connecting to Redis at {REDIS_URL}")
    
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        await r.ping()
        logger.info("✅ Redis connected")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Redis: {e}")
        return

    orchestrator = AgentOrchestrator()

    # Handle shutdown signals
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def signal_handler():
        logger.info("🛑 Shutdown signal received")
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, signal_handler)
        except NotImplementedError:
            # Windows does not support add_signal_handler
            pass

    logger.info("👀 Worker ready and watching queue...")
    
    while not stop_event.is_set():
        try:
            # Blocking pop with timeout to allow checking stop_event
            # blpop returns (key, value) tuple or None
            # We use a short timeout to check for stop_event frequently
            result = await r.blpop(ANALYSIS_QUEUE_KEY, timeout=2)
            
            if result:
                _, task_json = result
                await process_task(orchestrator, task_json)
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            if not stop_event.is_set():
                logger.error(f"Redis error: {e}")
                await asyncio.sleep(5) # Wait before retrying

    await r.close()
    logger.info("Worker stopped")

if __name__ == "__main__":
    try:
        asyncio.run(worker())
    except KeyboardInterrupt:
        pass
