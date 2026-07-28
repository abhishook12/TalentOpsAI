import requests
import sys

API = 'http://127.0.0.1:8000'

s = requests.Session()
r = s.post(f'{API}/auth/login', json={'email': 'admin@talentops.com', 'password': 'Password123!', 'remember_me': False})
token = r.json().get('token')
headers = {'Authorization': f'Bearer {token}'}

# Get Active Sessions
print("\n--- Check 1: Fetching Active Sessions ---")
r = s.get(f'{API}/admin/devices/sessions/active', headers=headers)
sessions = r.json()
print(f"Admin sees {len(sessions)} active sessions globally.")
if len(sessions) == 0:
    print("FAILED: No active sessions found. Admin should at least see their own session.")
    sys.exit(1)

# Bulk Terminate an empty list to test the endpoint
print("\n--- Check 2: Testing Bulk Terminate Endpoint ---")
r = s.post(f'{API}/admin/devices/sessions/bulk-terminate', json={'session_ids': []}, headers=headers)
if r.status_code == 200:
    print("Bulk terminate accepts empty list successfully.")
else:
    print(f"FAILED bulk terminate: {r.text}")
    sys.exit(1)

# Clear All sessions (except current admin)
print("\n--- Check 3: Testing Terminate All ---")
r = s.delete(f'{API}/admin/devices/sessions/all', headers=headers)
if r.status_code == 200:
    print(f"Terminate All successful: {r.json()}")
else:
    print(f"FAILED terminate all: {r.text}")
    sys.exit(1)

# Verify only 1 session remains (the admin's)
print("\n--- Final Verification ---")
r = s.get(f'{API}/admin/devices/sessions/active', headers=headers)
remaining = r.json()
print(f"Admin sees {len(remaining)} active session(s) globally after Terminate All.")
if len(remaining) == 1:
    print("SUCCESS: 3 verification checks passed successfully.")
else:
    print(f"FAILED: Expected exactly 1 active session remaining, but found {len(remaining)}.")
    sys.exit(1)
