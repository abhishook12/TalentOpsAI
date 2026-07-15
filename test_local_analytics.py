import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_tests():
    print("--- Testing Analytics API via TestClient ---")
    
    # 1. Start Session
    aid = "test-anon-123"
    sid = "test-session-123"
    
    res = client.post("/analytics/session/start", json={
        "anonymous_id": aid,
        "session_id": sid,
        "screen_size": "1920x1080",
        "timezone": "America/New_York",
        "referrer": "https://google.com",
        "user_agent": "Test Agent",
        "current_page": "/"
    }, headers={"X-Forwarded-For": "8.8.8.8"})
    
    print("Start Session:", res.status_code, res.json())
    
    # 2. Log Page View
    res = client.post("/analytics/session/event", json={
        "anonymous_id": aid,
        "session_id": sid,
        "event_type": "page_view",
        "current_page": "/dashboard",
        "previous_page": "/",
        "user_email": "test@talentopsai.com"
    })
    print("Log Event:", res.status_code, res.json())
    
    # 3. Heartbeat
    res = client.post("/analytics/session/heartbeat", json={
        "anonymous_id": aid,
        "session_id": sid,
        "status": "Active",
        "clicks_since_last": 5,
        "current_page": "/dashboard",
        "user_email": "test@talentopsai.com"
    })
    print("Heartbeat:", res.status_code, res.json())
    
    # 4. Check Live endpoint
    # Note: admin auth required, but let's see if we can bypass or just assume it works
    # Actually wait, our live endpoint requires auth. We can patch it or just check the DB.
    
    # 5. End Session
    res = client.post("/analytics/session/end", json={
        "session_id": sid
    })
    print("End Session:", res.status_code, res.json())

if __name__ == "__main__":
    run_tests()
