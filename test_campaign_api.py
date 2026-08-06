import requests
import jwt
from datetime import datetime, timezone, timedelta

# Create a direct JWT token
ALGORITHM = "HS256"
JWT_SECRET = "dev-jwt-secret-local"  # from .env

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=60*24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

token = create_access_token({"sub": "admin@talentops.ai", "role": "superadmin"})
headers = {"Authorization": f"Bearer {token}"}

API_URL = "http://127.0.0.1:8000/campaigns"

# 1. Create campaign
res = requests.post(f"{API_URL}/", json={"name": "Test Check 3"}, headers=headers)
print("Create Campaign:", res.status_code, res.text)
campaign_id = res.json()["campaign_id"]

# 2. Add an empty template (Check 1)
res = requests.post(f"{API_URL}/{campaign_id}/templates", json={"subject": "", "body": ""}, headers=headers)
print("Template Create Status:", res.status_code)
if res.status_code == 200:
    print("Check 1 PASSED: Can save empty template.")
else:
    print("Check 1 FAILED:", res.text)

# 3. Validate before send (Check 2)
res = requests.get(f"{API_URL}/{campaign_id}/validate-before-send", headers=headers)
data = res.json()
print("Validate Status:", res.status_code)
if not data.get("ready") and "MISSING_SUBJECT" in str(data.get("errors", [])):
    print("Check 2 PASSED: Validate endpoint catches empty template.")
else:
    print("Check 2 FAILED:", data)
