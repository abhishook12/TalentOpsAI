import requests
import sys

API = 'https://talentopsai-1.onrender.com'
s = requests.Session()

print("Logging in as Admin...")
try:
    r = s.post(f'{API}/auth/login', json={'email': 'admin@talentops.com', 'password': 'Password123!', 'remember_me': False}, timeout=10)
    if r.status_code != 200:
        print(f"Failed to login: {r.text}")
        sys.exit(1)
        
    token = r.json().get('token')
    headers = {'Authorization': f'Bearer {token}'}

    print("Fetching Dashboard KPIs...")
    r = s.get(f'{API}/analytics/dashboard', headers=headers, timeout=15)
    dashboard_total = r.json()['recruiters']['total']

    print("Fetching Data Quality KPIs...")
    dq = s.get(f'{API}/analytics/data-quality', headers=headers, timeout=15)
    dq_total = dq.json()['total_recruiters']

    print(f"\n--- VERIFICATION RESULTS ---")
    print(f"Dashboard Endpoint Total Recruiters: {dashboard_total}")
    print(f"Data Quality Endpoint Total Recruiters: {dq_total}")

    if dashboard_total > 150000 and dashboard_total == dq_total:
        print("SUCCESS: 3/3 checks passed. Data Quality matches Dashboard Data.")
    else:
        print("FAILED: Data is still missing or not synced.")
except Exception as e:
    print(f"Error: {e}")
