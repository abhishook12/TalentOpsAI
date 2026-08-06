import requests
import json

s = requests.Session()
login_res = s.post('https://talentopsai-1.onrender.com/auth/login', json={
    'email': 'admin@talentops.com',
    'password': 'admin123456',
    'remember_me': False
})
print("Login status:", login_res.status_code)

users_res = s.get('https://talentopsai-1.onrender.com/users/')
print("Users status:", users_res.status_code)

try:
    users_data = users_res.json()
    # Assuming users_data might be a dict with a 'users' key or just a list
    users_list = users_data.get('users', []) if isinstance(users_data, dict) else users_data
    
    bhim = [u for u in users_list if 'bsen' in u.get('email', '').lower()]
    print("Bhim user record:", json.dumps(bhim, indent=2, default=str))
except Exception as e:
    print("Error parsing:", e)
    print("Response text:", users_res.text[:500])
