import asyncio
import aiohttp
import time
import json
import statistics

BASE_URL = "http://127.0.0.1:8000/api"
LOGIN_DATA = {"email": "admin@talentops.com", "password": "adminpassword"}

async def test_endpoint(session, token, url, iterations=50, concurrency=10):
    headers = {"Authorization": f"Bearer {token}"}
    
    async def fetch(i):
        start = time.perf_counter()
        async with session.get(url, headers=headers) as response:
            await response.text()
            return time.perf_counter() - start

    # Run in batches according to concurrency
    latencies = []
    for i in range(0, iterations, concurrency):
        batch = [fetch(j) for j in range(i, min(i + concurrency, iterations))]
        results = await asyncio.gather(*batch)
        latencies.extend(results)
    
    return latencies

async def main():
    async with aiohttp.ClientSession() as session:
        # 1. Login
        async with session.post(f"{BASE_URL}/auth/login", json=LOGIN_DATA) as resp:
            data = await resp.json()
            token = data.get("access_token")
            if not token:
                print("Login failed:", data)
                return
            
        endpoints = [
            "/campaigns",
            "/recruiters",
            "/analytics/admin/summary",
        ]
        
        results = {}
        for ep in endpoints:
            print(f"Testing {ep}...")
            url = f"{BASE_URL}{ep}"
            latencies = await test_endpoint(session, token, url, iterations=30, concurrency=10)
            avg = statistics.mean(latencies)
            p90 = statistics.quantiles(latencies, n=10)[8]
            print(f"  {ep}: Avg={avg:.3f}s, p90={p90:.3f}s, Max={max(latencies):.3f}s")
            results[ep] = {"avg": avg, "p90": p90, "max": max(latencies)}
            
        with open("baseline_metrics.json", "w") as f:
            json.dump(results, f, indent=2)

if __name__ == "__main__":
    asyncio.run(main())
