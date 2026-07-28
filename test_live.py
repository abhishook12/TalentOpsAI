import requests
import sys

API = 'https://talentopsai-1.onrender.com'

def test_dashboard(email, password):
    s = requests.Session()
    r = s.post(f'{API}/auth/login', json={'email': email, 'password': password, 'remember_me': False})
    
    if 'pending_approval' in r.text:
        print(f"Device pending approval for {email} on live server! We cannot test without an admin approving it.")
        return -1

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

print("Testing LIVE API...")
admin_total = test_dashboard('admin@talentops.com', 'Password123!')
print(f"Admin sees: {admin_total}")

user_total = test_dashboard('user@talentops.com', 'User@TalentOps2026')
print(f"User sees: {user_total}")

if admin_total == user_total and admin_total > 0:
    print("SUCCESS: Data synchronization verified on LIVE SERVER. Both roles see the global database.")
else:
    print("FAILED: Data does not match on LIVE SERVER.")
    sys.exit(1)
