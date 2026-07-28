"""Verify the API returns updated company locations - 3 Times"""
import requests
import json

BASE = "http://127.0.0.1:8000"

# Login first
login = requests.post(f"{BASE}/auth/login", json={"email": "admin@talentops.com", "password": "admin"})
if login.status_code != 200:
    print(f"Login failed: {login.status_code} {login.text[:200]}")
    exit(1)

token = login.json().get("session_token") or login.json().get("token") or login.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

for pass_num in range(1, 4):
    print(f"\n=== PASS {pass_num} ===")
    resp = requests.get(f"{BASE}/analytics/companies-search", params={"limit": 10, "min_recruiters": 1, "skip": 0}, headers=headers)
    if resp.status_code != 200:
        print(f"API Error: {resp.status_code} {resp.text[:300]}")
        continue
    
    companies = resp.json()
    for c in companies[:10]:
        loc = c.get("location") or "NULL"
        print(f'  {c["company_name"]:35s} location={loc:30s} recruiters={c["recruiter_count"]}')
    
    # Also test company-states for Vaco (company_id we found earlier)
    states_resp = requests.get(f"{BASE}/analytics/company-states", params={"company_id": 23}, headers=headers)
    if states_resp.status_code == 200:
        states = states_resp.json()
        print(f"  Vaco states: {states[:5]}")
    else:
        print(f"  company-states ERROR: {states_resp.status_code} {states_resp.text[:200]}")
