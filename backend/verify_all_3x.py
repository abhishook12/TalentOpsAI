#!/usr/bin/env python
import urllib.request
import json
import time
import datetime

endpoints = [
    ("/analytics/data-quality", "Analytics KPIs (Unknowns=0)"),
    ("/analytics/recruiters-by-state", "Directory Map (States Covered)"),
    ("/companies/?limit=5", "Companies Directory (State Mapped)")
]

base = "http://127.0.0.1:8000"

print("STARTING STRICT 3-TIME CROSS-COMPONENT VERIFICATION PROTOCOL...\n")

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
                elif path == "/analytics/recruiters-by-state":
                    print(f"[{name}] -> Status: {status} | Mapped Regions Count: {len(data)}")
                elif path == "/companies/?limit=5":
                    states = [d.get("state") for d in data[:4]]
                    print(f"[{name}] -> Status: {status} | Top Company States: {states}")
        except Exception as e:
            print(f"[{name}] -> FAILED: {e}")
    print()
    if i < 3:
        time.sleep(2)

print("3-TIME CROSS-COMPONENT VERIFICATION PROTOCOL COMPLETE.")
