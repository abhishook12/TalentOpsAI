import asyncio
import sys
import logging
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("sentinel_runner")

from app.services.sentinel_engine import sentinel_engine

async def main():
    logger.info("Starting Sentinel Engine Background Daemon...")
    sentinel_engine.start()
    
    try:
        while True:
            # Keep the main thread alive while the asyncio task runs in the background
            await asyncio.sleep(60)
            logger.info(f"Sentinel Engine heartbeat. Running status: {sentinel_engine.running}")
    except KeyboardInterrupt:
        logger.info("Interrupt received, stopping Sentinel Engine...")
        sentinel_engine.stop()
        await asyncio.sleep(2) # Allow time for graceful shutdown
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    asyncio.run(main())
