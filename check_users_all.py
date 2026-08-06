import requests
import json

s = requests.Session()
login_res = s.post('https://talentopsai-1.onrender.com/auth/login', json={
    'email': 'admin@talentops.com',
    'password': 'admin123456',
    'remember_me': False
})
users_res = s.get('https://talentopsai-1.onrender.com/users/')
users_data = users_res.json()
if isinstance(users_data, dict):
    users_list = users_data.get('items', [])
else:
    users_list = users_data

print("Total users:", len(users_list))
emails = [u.get('email') for u in users_list]
print("Emails:", json.dumps(emails, indent=2))
