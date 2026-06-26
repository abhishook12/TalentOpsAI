#!/usr/bin/env python
import urllib.request
import time
import json
import datetime

url = "http://127.0.0.1:8000/analytics/companies-search?limit=200&skip=0&min_recruiters=1"

print("STARTING 3-TIME DIRECTORY PAGE LOAD SPEED AUDIT...\n")

for i in range(1, 4):
    start = time.time()
    now = datetime.datetime.now().isoformat()
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            elapsed = round((time.time() - start) * 1000, 2)
            print(f"--- [SPEED CHECK #{i} - Timestamp: {now}] ---")
            print(f"HTTP Status:     {resp.status} OK")
            print(f"Companies Count: {len(data)}")
            print(f"Response Time:   {elapsed} ms\n")
    except Exception as e:
        print(f"--- [SPEED CHECK #{i} FAILED: {e}] ---\n")
    if i < 3:
        time.sleep(1)

print("3-TIME DIRECTORY SPEED AUDIT COMPLETE.")
