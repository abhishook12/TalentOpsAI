import asyncio
import sys
import logging

logging.basicConfig(level=logging.INFO)

from app.services.sentinel_engine import sentinel_engine

async def main():
    print("Starting Sentinel Engine...")
    sentinel_engine.start()
    
    # Let it run for 10 seconds
    await asyncio.sleep(10)
    
    print("Stopping Sentinel Engine...")
    sentinel_engine.stop()
    print("Test Complete.")

if __name__ == "__main__":
    asyncio.run(main())
