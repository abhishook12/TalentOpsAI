import requests
import json

s = requests.Session()
login_res = s.post('https://talentopsai-1.onrender.com/auth/login', json={
    'email': 'admin@talentops.com',
    'password': 'admin123456',
    'remember_me': False
})
print("Login status:", login_res.status_code)

devices_res = s.get('https://talentopsai-1.onrender.com/users/')
print("Devices status:", devices_res.status_code)
devices = devices_res.json()

print(f"Total devices: {len(devices)}")
pending = [d for d in devices if d['status'] == 'Pending']
print(f"Pending devices: {len(pending)}")

for p in pending:
    print(f"Pending User: {p.get('user_email')}")
    
# Let's also check if Bhim's email is in any of the devices
bhim_devices = [d for d in devices if 'bsen' in d.get('user_email', '').lower()]
print(f"Bhim devices: {len(bhim_devices)}")
for d in bhim_devices:
    print(f"- {d.get('user_email')} | Status: {d.get('status')}")
