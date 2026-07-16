import requests
import json
import uuid

api_url = "https://talentopsai-1.onrender.com"
session = requests.Session()

# 1. Login as the newly created test user to get their cookies
res = session.post(f"{api_url}/auth/login", json={"email": "e2e_test_1784209054088@talentops.com", "password": "Password123!"})
print("Login status:", res.status_code)

# 2. Simulate sending an analytics event exactly like the frontend does
anon_id = "test_anon_id_" + str(uuid.uuid4())
sess_id = "test_sess_id_" + str(uuid.uuid4())

payload = {
    "anonymous_id": anon_id,
    "session_id": sess_id,
    "user_email": "e2e_test_1784209054088@talentops.com",
    "screen_size": "1920x1080",
    "timezone": "UTC",
    "referrer": "",
    "user_agent": "Python Requests",
    "current_page": "/"
}
res2 = session.post(f"{api_url}/analytics/session/start", json=payload)
print("Analytics /start status:", res2.status_code)
print("Analytics /start body:", res2.text)

# 3. Simulate page_view event
event_payload = {
    "anonymous_id": anon_id,
    "session_id": sess_id,
    "user_email": "e2e_test_1784209054088@talentops.com",
    "event_type": "page_view",
    "current_page": "/campaigns",
    "previous_page": "/"
}
res3 = session.post(f"{api_url}/analytics/session/event", json=event_payload)
print("Analytics /event status:", res3.status_code)
print("Analytics /event body:", res3.text)

