import requests
import time

url = 'http://127.0.0.1:1337/send-bulk'
payload = {
    "recipients": [
        {"email": "fake1@example.com", "recruiter_name": "Fake One"},
        {"email": "fake2@example.com", "recruiter_name": "Fake Two"}
    ],
    "subject": "Test Verification",
    "body": "Hello this is a test"
}

for i in range(1, 5):
    print(f"Test {i}...")
    try:
        r = requests.post(url, json=payload)
        print(f"Status: {r.status_code}, Response: {r.text}")
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(2)
