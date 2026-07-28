import requests
import sys

API = 'https://talentopsai-1.onrender.com'

s = requests.Session()

print("Registering test3@talentops.com...")
reg = s.post(f'{API}/auth/register', json={
    'first_name': 'Test',
    'last_name': 'Three',
    'email': 'test3@talentops.com',
    'password': 'Password123!',
    'company': 'TalentOps'
})
print("Register response:", reg.status_code, reg.text)

print("Logging in...")
r = s.post(f'{API}/auth/login', json={'email': 'test3@talentops.com', 'password': 'Password123!', 'remember_me': False})
print("Login response:", r.status_code, r.text)

if r.status_code == 200:
    token = r.json().get('token')
    headers = {'Authorization': f'Bearer {token}'}
    dash = s.get(f'{API}/analytics/dashboard', headers=headers)
    print("Dashboard:", dash.status_code, dash.text)
    
    dq = s.get(f'{API}/analytics/data-quality', headers=headers)
    print("Data Quality:", dq.status_code, dq.text)
