import requests
import time

try:
    print("Testing /analytics/dashboard...")
    start = time.time()
    res = requests.get("http://127.0.0.1:8000/analytics/dashboard", timeout=10)
    print(f"Status: {res.status_code}")
    print(f"Time: {time.time() - start:.2f}s")
    print(res.text[:200])
except Exception as e:
    print(f"Error: {e}")

try:
    print("\nTesting /analytics/data-quality...")
    start = time.time()
    res = requests.get("http://127.0.0.1:8000/analytics/data-quality", timeout=10)
    print(f"Status: {res.status_code}")
    print(f"Time: {time.time() - start:.2f}s")
    print(res.text[:200])
except Exception as e:
    print(f"Error: {e}")
