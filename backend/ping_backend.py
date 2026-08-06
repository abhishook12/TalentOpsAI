import subprocess
import time
import requests
import sys

print("Starting backend...")
proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

try:
    print("Waiting for boot...")
    time.sleep(5)
    
    print("Pinging health endpoint...")
    resp = requests.get("http://127.0.0.1:8000/api/health")
    resp.raise_for_status()
    print("Health check passed:", resp.json())
    
finally:
    print("Terminating backend...")
    proc.terminate()
    proc.wait(timeout=5)
    print("Done.")
