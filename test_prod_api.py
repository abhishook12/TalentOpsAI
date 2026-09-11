import requests
import json

url = "https://talentopsai-1.onrender.com/recruiters/extension/batch"
payload = {
  "device_id": "test-device-123",
  "contacts": [
    {
      "recruiter_name": "Test Tester",
      "email": "test@test.com",
      "skills": ["Python", "JavaScript"]
    }
  ]
}

try:
    res = requests.post(url, json=payload, headers={"Content-Type": "application/json"})
    print("Status:", res.status_code)
    print("Response:", res.text)
except Exception as e:
    print("Error:", e)
