import asyncio
import os
import sys

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.services.identity_engine import identity_engine

async def main():
    print("Starting identity engine job...", flush=True)
    identity_engine.is_running = True
    # Directly await the internal job to run it synchronously for the script
    
    # We can also monitor progress by running a parallel task
    async def monitor():
        while identity_engine.is_running:
            print(f"State: {identity_engine.state}", flush=True)
            await asyncio.sleep(5)
            
    monitor_task = asyncio.create_task(monitor())
    await identity_engine._run_job()
    identity_engine.is_running = False
    
    print("Job finished!", flush=True)
    print("Final State:", identity_engine.state, flush=True)

if __name__ == "__main__":
    asyncio.run(main())
