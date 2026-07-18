import requests
API_URL = "https://talentopsai-1.onrender.com"
import sys

cid = 101
print(f"Checking Campaign {cid}")

res = requests.post(f"{API_URL}/auth/login", data={"username": "admin@talentops.com", "password": "1012"})
if res.status_code != 200:
    print("Login failed")
    sys.exit(1)
token = res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

res2 = requests.get(f"{API_URL}/campaigns/{cid}/progress", headers=headers)
print("Progress:", res2.text)

res3 = requests.get(f"{API_URL}/campaigns", headers=headers)
camps = res3.json()
for c in camps:
    if c.get("campaign_id") == cid:
        print("Campaign Data:", c)
