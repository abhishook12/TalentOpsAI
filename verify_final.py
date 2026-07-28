import requests
import sys

API = 'https://talentopsai-1.onrender.com'

s = requests.Session()
email = 'test3@talentops.com'
password = 'Password123!'

print(f"Logging in as {email}...")
r = s.post(f'{API}/auth/login', json={'email': email, 'password': password, 'remember_me': False})

if 'pending_approval' in r.text:
    print("Device pending approval.")
    sys.exit(1)

if r.status_code != 200:
    print(f"Failed to login: {r.text}")
    sys.exit(1)
    
token = r.json().get('token')
headers = {'Authorization': f'Bearer {token}'}

print("Fetching Dashboard KPIs...")
r = s.get(f'{API}/analytics/dashboard', headers=headers)
if r.status_code != 200:
    print(f"Failed dashboard: {r.text}")
    sys.exit(1)
dashboard_total = r.json()['recruiters']['total']

print("Fetching Data Quality KPIs...")
dq = s.get(f'{API}/analytics/data-quality', headers=headers)
if dq.status_code != 200:
    print(f"Failed data quality: {dq.text}")
    sys.exit(1)
dq_total = dq.json()['total_recruiters']

print(f"\n--- VERIFICATION RESULTS ---")
print(f"Dashboard Endpoint Total Recruiters: {dashboard_total}")
print(f"Data Quality Endpoint Total Recruiters: {dq_total}")

if dashboard_total > 0 and dashboard_total == dq_total:
    print("SUCCESS: 3/3 checks passed. Data is synchronized and visible to the standard user on LIVE!")
else:
    print("FAILED: Data is still missing or not synced.")
