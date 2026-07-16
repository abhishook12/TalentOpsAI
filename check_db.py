import requests

api_url = "https://talentopsai-1.onrender.com"
res = requests.post(f"{api_url}/auth/login", json={"email": "admin@talentops.com", "password": "adminpassword"})
token = res.json()["token"]
headers = {"Authorization": f"Bearer {token}"}
res2 = requests.get(f"{api_url}/admin/visitor-analytics/sessions", headers=headers)
data = res2.json()
emails = [s.get("user_email") for s in data.get("items", []) if s.get("user_email")]
print("Emails in DB: ", emails[:20])
