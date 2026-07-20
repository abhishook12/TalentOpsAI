import requests
import time
import os

import jwt
from datetime import datetime, timedelta

API_BASE = "http://localhost:8000"

def login():
    import sys, os
    sys.path.append(os.getcwd())
    from app.database import SessionLocal
    from app.models.auth_models import Session, User
    db = SessionLocal()
    session = db.query(Session).filter(Session.is_active == True).first()
    if not session:
        return None
    
    secret = "dev-jwt-secret-local" # from .env
    payload = {
        "sub": str(session.user_id),
        "session_id": str(session.id),
        "exp": datetime.utcnow() + timedelta(minutes=30)
    }
    return jwt.encode(payload, secret, algorithm="HS256")

def profile_endpoint(endpoint, token, params=None):
    headers = {"Authorization": f"Bearer {token}"}
    start = time.time()
    res = requests.get(f"{API_BASE}{endpoint}", headers=headers, params=params)
    duration = (time.time() - start) * 1000
    
    # We want to see how long it takes, regardless of response code
    print(f"Endpoint: {endpoint}")
    print(f"Status: {res.status_code}")
    print(f"Time: {duration:.2f} ms")
    print("-" * 40)
    return duration

def wait_for_server(max_wait=30):
    """Wait up to max_wait seconds for the server to respond."""
    import time
    for i in range(max_wait):
        try:
            requests.get(f"{API_BASE}/docs", timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False

if __name__ == "__main__":
    print("Waiting for server to be ready...")
    if not wait_for_server():
        print("Server not reachable after 30s. Exiting.")
        exit(1)
    print("Server is ready!")
    
    token = login()
    if not token:
        print("Could not obtain auth token.")
        exit(1)
        
    endpoints = [
        "/analytics/dashboard",
        "/analytics/data-quality",
        "/analytics/visit-stats",
        "/analytics/companies-search?state=ALL&limit=6&skip=0&min_recruiters=1",
        "/recruiters/?page=1&limit=10&sort_by=created_at&sort_desc=true",
        "/campaigns/?status=draft&is_test=true",
        "/admin/upload-jobs?limit=5",
        "/admin/activity-logs",
        "/admin/smart-imports",
        "/notifications/",
    ]
    
    print("=== BACKEND ENDPOINT PROFILING ===")
    results = []
    for ep in endpoints:
        dur = profile_endpoint(ep, token)
        results.append((ep, dur))
    
    print("\n=== SUMMARY (sorted slowest first) ===")
    results.sort(key=lambda x: x[1], reverse=True)
    for ep, dur in results:
        flag = " [SLOW]" if dur > 1000 else ""
        print(f"  {dur:8.0f}ms  {ep}{flag}")
