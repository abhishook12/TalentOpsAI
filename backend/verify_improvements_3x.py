#!/usr/bin/env python
import urllib.request
import json
import time
import datetime

endpoints = [
    ("/analytics/data-quality", "Analytics KPIs"),
    ("/recruiters/?limit=5", "Recruiters List View"),
    ("/analytics/companies-search?limit=200&skip=0&min_recruiters=1", "Directory Page")
]

base = "http://127.0.0.1:8000"

print("STARTING STRICT 3-TIME POST-IMPROVEMENT AUDIT...\n")

for i in range(1, 4):
    now = datetime.datetime.now().isoformat()
    print(f"==========================================================")
    print(f"      VERIFICATION SWEEP #{i} [Timestamp: {now}]")
    print(f"==========================================================")
    
    for path, name in endpoints:
        url = base + path
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                status = resp.status
                if path == "/analytics/data-quality":
                    unk = data.get("unknown_state_count")
                    tot = data.get("total_recruiters")
                    print(f"[{name}] -> Status: {status} | Unknowns: {unk} / {tot}")
                elif path == "/recruiters/?limit=5":
                    items = data if isinstance(data, list) else data.get("results", data.get("items", []))
                    names = [r.get("recruiter_name") for r in items[:3]]
                    print(f"[{name}] -> Status: {status} | Top Recruiter Names: {names}")
                elif "companies-search" in path:
                    print(f"[{name}] -> Status: {status} | Companies Returned: {len(data)}")
        except Exception as e:
            print(f"[{name}] -> FAILED: {e}")
    print()
    if i < 3:
        time.sleep(1)

print("3-TIME POST-IMPROVEMENT VERIFICATION PROTOCOL COMPLETE.")
