"""
Test live connectivity to Render backend for extension batch ingestion.
"""

import requests

url = "https://talentopsai-1.onrender.com"

print(f"Checking {url}/health...")
try:
    r = requests.get(f"{url}/health", timeout=10)
    print(f"Health Status: {r.status_code}, Response: {r.text[:200]}")
except Exception as e:
    print(f"Health check failed: {e}")

print(f"\nChecking {url}/recruiters/extension/auto-activate...")
try:
    r = requests.post(f"{url}/recruiters/extension/auto-activate", timeout=10)
    print(f"Auto-activate Status: {r.status_code}, Response: {r.text[:200]}")
    if r.status_code == 200:
        token = r.json().get("access_token") or r.json().get("token")
        print(f"Token obtained: {token[:20]}...")
        
        # Test batch post
        batch_url = f"{url}/recruiters/extension/batch"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {
            "device_id": "test-verify-node-01",
            "contacts": [
                {
                    "recruiter_name": "Meagan Garnett",
                    "title": "Professional Recruiter",
                    "company_name": "Brooksource",
                    "location": "Greater Birmingham, Alabama Area",
                    "source_url": "https://www.linkedin.com/in/meagangarnett/",
                    "confidence": 99
                }
            ]
        }
        br = requests.post(batch_url, json=payload, headers=headers, timeout=10)
        print(f"Batch POST Status: {br.status_code}, Response: {br.text[:300]}")
except Exception as e:
    print(f"Auto-activate/batch check failed: {e}")
