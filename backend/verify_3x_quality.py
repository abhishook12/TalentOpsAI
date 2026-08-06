import time
import urllib.request
import json

def verify(attempt):
    print(f"--- Attempt {attempt} ---")
    
    # 1. Check quality-metrics
    try:
        req = urllib.request.Request("http://localhost:8000/analytics/quality-metrics")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            print(f"✅ Quality Metrics OK: Health={data.get('overall_health')}%")
    except Exception as e:
        print(f"❌ Quality Metrics Error: {e}")
        return False
        
    # 2. Check repair-logs
    try:
        req = urllib.request.Request("http://localhost:8000/analytics/repair-logs?limit=5")
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            print(f"✅ Repair Logs OK: Count={len(data.get('logs', []))}")
    except Exception as e:
        print(f"❌ Repair Logs Error: {e}")
        return False
        
    return True

successes = 0
for i in range(1, 4):
    if verify(i):
        successes += 1
    time.sleep(1)

print("\n=== FINAL RESULT ===")
if successes == 3:
    print("SUCCESS: Verified 3 times successfully.")
else:
    print(f"FAILURE: Only verified {successes}/3 times successfully.")
