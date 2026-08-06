import requests
import json

s = requests.Session()
login_res = s.post('https://talentopsai-1.onrender.com/auth/login', json={
    'email': 'admin@talentops.com',
    'password': 'admin123456',
    'remember_me': False
})
print("Login status:", login_res.status_code)
# This returns 200 for admin, so no device_id cookie flow is tested.

# Let's test with a pending user to see if the device_id cookie is returned and then we call complete-device-approval.
# We don't have Bhim's password.
# But wait! I can just hit the PROD API with a wrong password for Bhim to see if it even reaches the pending step? No, it will fail auth.

# Wait, let's write a python script to login as a test user, but using our local API, wait, I can't start local API because no local DB.
