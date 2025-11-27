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
FAILED_QUEUE_KEY = "analysis_tasks:failed"  # Dead Letter Queue

async def process_task(orchestrator: AgentOrchestrator, task_json: str):
    try:
        task = json.loads(task_json)
        package = task.get("package")
        version = task.get("version", "latest")
        force = task.get("force", False)
        ecosystem = task.get("ecosystem", "npm")
        
        cve_id = task.get("cve_id")
        
        if not package and not cve_id:
            logger.warning("Invalid task received: missing package and cve_id")
            return
        
        target_desc = f"{ecosystem}:{package}@{version}" if package else f"CVE-only:{cve_id}"
        logger.info(f"🚀 Processing task for {target_desc}")
        
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
            ecosystem=ecosystem,
            cve_id=cve_id
        )
        logger.info(f"✅ Task completed for {package}")

    except json.JSONDecodeError:
        logger.error(f"Failed to decode task JSON: {task_json}")
        raise  # Re-raise to trigger DLQ
    except Exception as e:
        logger.error(f"❌ Error processing task: {e}")
        traceback.print_exc()
        raise  # Re-raise to trigger DLQ

async def worker():
    logger.info(f"🔧 Starting worker, connecting to Redis at {REDIS_URL}")
    
    # Retry logic for Redis connection
    r = None
    max_connection_retries = 5
    for attempt in range(1, max_connection_retries + 1):
        try:
            r = redis.from_url(REDIS_URL, decode_responses=True)
            await r.ping()
            logger.info("✅ Redis connected")
            break
        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis (attempt {attempt}/{max_connection_retries}): {e}")
            if attempt == max_connection_retries:
                logger.critical("Max connection retries reached. Exiting worker.")
                return
            await asyncio.sleep(5)  # Wait before retrying

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
    
    print(f"DEBUG: REDIS_URL={REDIS_URL}", flush=True)
    print(f"DEBUG: ANALYSIS_QUEUE_KEY={ANALYSIS_QUEUE_KEY}", flush=True)
    try:
        keys = await r.keys("*")
        print(f"DEBUG: Keys in Redis: {keys}", flush=True)
        len_queue = await r.llen(ANALYSIS_QUEUE_KEY)
        print(f"DEBUG: Queue length: {len_queue}", flush=True)
        await r.set("worker_test_key", "hello_from_worker")
        print("DEBUG: Set worker_test_key", flush=True)
    except Exception as e:
        print(f"DEBUG: Error checking keys: {e}", flush=True)

    while not stop_event.is_set():
        try:
            # Blocking pop with timeout to allow checking stop_event
            # blpop returns (key, value) tuple or None
            # We use a short timeout to check for stop_event frequently
            print("DEBUG: Waiting for task...", flush=True)
            result = await r.blpop(ANALYSIS_QUEUE_KEY, timeout=2)
            print(f"DEBUG: Popped result: {result}", flush=True)
            
            if result:
                _, task_json = result
                
                # DLQ Strategy: Wrap processing in try-except
                try:
                    await process_task(orchestrator, task_json)
                except Exception as e:
                    # Task processing failed - push to Dead Letter Queue
                    logger.error(f"💀 Task failed and will be moved to DLQ: {e}")
                    logger.error("Full traceback:")
                    logger.error(traceback.format_exc())
                    
                    try:
                        # Attempt to add error metadata to payload
                        failed_task = json.loads(task_json)
                        failed_task["error_msg"] = str(e)
                        failed_task["error_timestamp"] = asyncio.get_event_loop().time()
                        failed_task["error_traceback"] = traceback.format_exc()
                        failed_payload = json.dumps(failed_task)
                    except Exception:
                        # If we can't parse/modify, save original payload
                        failed_payload = task_json
                    
                    # Push to Dead Letter Queue
                    await r.rpush(FAILED_QUEUE_KEY, failed_payload)
                    logger.warning(f"📮 Failed task pushed to DLQ: {FAILED_QUEUE_KEY}")
            
        except asyncio.CancelledError:
            break
        except redis.RedisError as e:
            # Redis connection errors - retry after delay
            if not stop_event.is_set():
                logger.error(f"Redis connection error: {e}")
                logger.info("Attempting to reconnect to Redis in 5 seconds...")
                await asyncio.sleep(5)
                try:
                    await r.ping()
                    logger.info("✅ Redis connection restored")
                except Exception:
                    logger.error("Redis reconnection failed, will retry on next iteration")
        except Exception as e:
            # Catch-all for unexpected errors in main loop
            if not stop_event.is_set():
                logger.error(f"Unexpected error in worker loop: {e}")
                logger.error(traceback.format_exc())
                await asyncio.sleep(5)  # Wait before continuing

    await r.close()
    logger.info("Worker stopped")

if __name__ == "__main__":
    try:
        asyncio.run(worker())
    except KeyboardInterrupt:
        pass
