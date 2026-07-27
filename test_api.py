import requests
import json

r = requests.post('http://127.0.0.1:8000/auth/login', json={'email': 'admin@talentops.com', 'password': '1012'})
token = r.json().get('token')
headers = {'Authorization': f'Bearer {token}'}

print("Testing /analytics/companies-search...")
res = requests.get('http://127.0.0.1:8000/analytics/companies-search?limit=10', headers=headers)
print("Status Code:", res.status_code)
if res.status_code == 200:
    data = res.json()
    print("SUCCESS! The database error is gone.")
    print("Number of companies returned:", len(data))
    if len(data) > 0:
        print("First company:", data[0]['company_name'])
else:
    print("Error:", res.text)
