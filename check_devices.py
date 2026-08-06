import requests
import time

login_url = 'https://talentopsai-1.onrender.com/auth/login'
devices_url = 'https://talentopsai-1.onrender.com/admin/devices/'

print('Logging into production to get Admin Token...')
resp = requests.post(login_url, json={'email': 'admin@talentops.com', 'password': 'admin123456', 'remember_me': False})
token = resp.json().get('token')

print('\nTesting /admin/devices/ 3 times (Rule 11)...')
for i in range(1, 4):
    try:
        dev_resp = requests.get(devices_url, headers={'Authorization': f'Bearer {token}'}, timeout=10)
        if dev_resp.status_code == 200:
            devices = dev_resp.json()
            pending_devices = [d for d in devices if d.get('status') == 'Pending' or d.get('status') == 'pending_approval']
            print(f'Check {i}: Status {dev_resp.status_code} OK | Total Devices Loaded: {len(devices)} | Pending Devices Found: {len(pending_devices)}')
            if i == 1 and pending_devices:
                print(f"         Sample Pending Device Email: {pending_devices[0].get('user_email')}")
        else:
            print(f'Check {i}: Status {dev_resp.status_code} ERROR: {dev_resp.text}')
    except Exception as e:
        print(f'Check {i}: Error {e}')
    time.sleep(1)
