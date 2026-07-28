import requests
import sys
import uuid
import sqlalchemy
import time
import re

API = 'https://talentopsai-1.onrender.com'
s = requests.Session()

email = f'user_{uuid.uuid4().hex[:8]}@example.com'
password = 'Password123!'

print(f"Registering as {email}...")
res = s.post(f'{API}/auth/register', json={
    'email': email,
    'password': password,
    'first_name': 'Test',
    'last_name': 'User'
})

print("Marking user as Active in DB...")
DATABASE_URL = "postgresql+psycopg://postgres.dcqvsvgrdsrgnbwwssup:sPMFmD3XYX6RW2PD@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres"
engine = sqlalchemy.create_engine(DATABASE_URL)
with engine.connect() as conn:
    conn.execute(sqlalchemy.text(f"UPDATE users SET status = 'Active' WHERE email = '{email}'"))
    conn.commit()

print("Logging in to trigger device approval...")
r = s.post(f'{API}/auth/login', json={'email': email, 'password': password, 'remember_me': False})
print("Login Response 1:", r.status_code, r.text)

if r.status_code == 202 and 'pending_approval' in r.text:
    device_id = r.json()['device_id']
    cookie_str = r.json()['cookie']
    m = re.search(r"device_id=([^;]+)", cookie_str)
    cookie_val = m.group(1) if m else cookie_str
    
    print(f"Approving device_id={device_id} in DB...")
    with engine.connect() as conn:
        conn.execute(sqlalchemy.text(f"UPDATE trusted_devices SET status = 'Trusted' WHERE id = {device_id}"))
        conn.commit()
    print("Re-logging in after approval...")
    r = s.post(f'{API}/auth/login', json={'email': email, 'password': password, 'remember_me': False}, cookies={'device_id': cookie_val})
    print("Login Response 2:", r.status_code, r.text)

token = r.json().get('token')
if not token:
    print("NO TOKEN!")
    sys.exit(1)

headers = {'Authorization': f'Bearer {token}'}

print("Fetching User Dashboard KPIs...")
r = s.get(f'{API}/analytics/dashboard', headers=headers, timeout=20)
dashboard_total = r.json()['recruiters']['total']

print(f"\n--- USER VERIFICATION RESULTS ---")
print(f"Dashboard Endpoint Total Recruiters: {dashboard_total}")

if dashboard_total == 284136:
    print("SUCCESS: User Dashboard matches Admin Dashboard!")
else:
    print(f"FAILED: User dashboard shows {dashboard_total}")
