#!/usr/bin/env python
import urllib.request
import json
import time
import datetime

url = "http://127.0.0.1:8000/analytics/data-quality"

print("STARTING STRICT 3-TIME API VERIFICATION PROTOCOL...")

for i in range(1, 4):
    time.sleep(2)
    now = datetime.datetime.now().isoformat()
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"\n--- [VERIFICATION CHECK #{i} - Timestamp: {now}] ---")
            print(f"HTTP Status: {resp.status}")
            print(f"Known State Count:   {data.get('known_state_count')}")
            print(f"Unknown State Count: {data.get('unknown_state_count')}")
            print(f"Total Recruiters:    {data.get('total_recruiters')}")
            print(f"Real Emails:         {data.get('real_emails')}")
    except Exception as e:
        print(f"\n[VERIFICATION CHECK #{i} FAILED: {e}]")

print("\n3-TIME VERIFICATION COMPLETE.")
