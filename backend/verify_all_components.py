#!/usr/bin/env python
import urllib.request
import json

endpoints = [
    ("/analytics/data-quality", "Analytics Data Quality KPIs"),
    ("/analytics/recruiters-by-state", "Directory & Analytics State Map"),
    ("/recruiters/?limit=5", "Recruiters Directory List"),
    ("/companies/?limit=5", "Companies Directory List"),
    ("/updates/status", "System Status & Updates")
]

base = "http://127.0.0.1:8000"

print("STARTING FULL CROSS-COMPONENT API AUDIT...")

for path, desc in endpoints:
    url = base + path
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode('utf-8')
            data = json.loads(raw)
            print(f"\n--- [COMPONENT: {desc} ({path})] ---")
            print(f"HTTP Status: {resp.status} OK")
            if isinstance(data, dict):
                if "unknown_state_count" in data:
                    print(f"   -> Unknown State Count: {data['unknown_state_count']}")
                if "total_recruiters" in data:
                    print(f"   -> Total Recruiters:    {data['total_recruiters']}")
                if "status" in data:
                    print(f"   -> Status:              {data['status']}")
                if "items" in data:
                    print(f"   -> Returned Items Count:{len(data['items'])}")
            elif isinstance(data, list):
                print(f"   -> Returned List Length: {len(data)}")
                if len(data) > 0 and isinstance(data[0], dict) and "state" in data[0]:
                    states = [d['state'] for d in data[:5]]
                    print(f"   -> Top Covered States:   {states}")
    except Exception as e:
        print(f"\n[COMPONENT FAILED: {desc} ({path}) - Error: {e}]")

print("\nCROSS-COMPONENT AUDIT COMPLETE.")
