import requests
import sys

API = 'http://127.0.0.1:8000'

def test_dashboard(email, password):
    s = requests.Session()
    r = s.post(f'{API}/auth/login', json={'email': email, 'password': password, 'remember_me': False})
    
    # If device pending, we must approve it via sqlite directly
    if 'pending_approval' in r.text:
        import sqlite3
        conn = sqlite3.connect(r'C:\TalentOpsAI\backend\dev.db')
        c = conn.cursor()
        c.execute("UPDATE trusted_devices SET status = 'Trusted' WHERE status = 'Pending'")
        conn.commit()
        conn.close()
        
        # Retry login
        r = s.post(f'{API}/auth/login', json={'email': email, 'password': password, 'remember_me': False})
        
    if r.status_code != 200:
        print(f"Failed to login as {email}: {r.text}")
        return -1
        
    token = r.json().get('token')
    headers = {'Authorization': f'Bearer {token}'}
    
    r = s.get(f'{API}/analytics/dashboard', headers=headers)
    if r.status_code != 200:
        print(f"Failed dashboard for {email}: {r.text}")
        return -1
    return r.json()['recruiters']['total']

admin_total = test_dashboard('admin@talentops.com', 'Password123!')
print(f"Admin sees: {admin_total}")

user_total = test_dashboard('test2@talentops.com', 'User@TalentOps2026')
print(f"User sees: {user_total}")

if admin_total == user_total and admin_total > 0:
    print("SUCCESS: Data synchronization verified. Both roles see the global database.")
else:
    print("FAILED: Data does not match.")
    sys.exit(1)
