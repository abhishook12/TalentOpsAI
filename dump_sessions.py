import requests

api_url = "https://talentopsai-1.onrender.com"
session = requests.Session()
res = session.post(f"{api_url}/auth/login", json={"email": "admin@talentops.com", "password": "adminpassword"})
res2 = session.get(f"{api_url}/admin/visitor-analytics/sessions")
data = res2.json()
print("SESSIONS JSON: ", data)
