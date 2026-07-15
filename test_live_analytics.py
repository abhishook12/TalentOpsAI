import time
import requests
import uuid

def simulate_visitor(base_url, user_agent, page_sequence, email=None):
    aid = str(uuid.uuid4())
    sid = str(uuid.uuid4())
    
    print(f"\n--- Simulating Session ---")
    print(f"Session ID: {sid}")
    print(f"Anonymous ID: {aid}")
    print(f"Email: {email}")
    
    headers = {
        "User-Agent": user_agent,
        "X-Anonymous-ID": aid,
        "X-Session-ID": sid,
        "Content-Type": "application/json"
    }

    # 1. Start Session
    res = requests.post(f"{base_url}/analytics/session/start", json={
        "anonymous_id": aid,
        "session_id": sid,
        "user_email": email,
        "screen_size": "1920x1080",
        "timezone": "America/New_York",
        "referrer": "https://google.com",
        "user_agent": user_agent,
        "current_page": page_sequence[0]
    }, headers=headers)
    print("Start:", res.status_code, res.text)
    
    prev_page = page_sequence[0]
    
    # 2. Page Views
    for page in page_sequence[1:]:
        time.sleep(2)
        res = requests.post(f"{base_url}/analytics/session/event", json={
            "anonymous_id": aid,
            "session_id": sid,
            "event_type": "page_view",
            "current_page": page,
            "previous_page": prev_page,
            "user_email": email
        }, headers=headers)
        print(f"View {page}:", res.status_code, res.text)
        prev_page = page
        
    # 3. Heartbeat with Clicks
    time.sleep(1)
    res = requests.post(f"{base_url}/analytics/session/heartbeat", json={
        "anonymous_id": aid,
        "session_id": sid,
        "status": "Active",
        "clicks_since_last": 14,
        "current_page": prev_page,
        "user_email": email
    }, headers=headers)
    print("Heartbeat:", res.status_code, res.text)
    
    # 4. End Session
    time.sleep(1)
    res = requests.post(f"{base_url}/analytics/session/end", json={
        "session_id": sid
    }, headers=headers)
    print("End:", res.status_code, res.text)
    
    return sid

if __name__ == "__main__":
    LIVE_URL = "https://talentopsai-1.onrender.com"
    
    # Wait for deployment
    print("Waiting 15 seconds for Render backend deployment...")
    time.sleep(15)
    
    sid1 = simulate_visitor(
        LIVE_URL, 
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36", 
        ["/", "/about", "/pricing"]
    )
    
    sid2 = simulate_visitor(
        LIVE_URL, 
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15", 
        ["/login", "/dashboard", "/admin"],
        email="admin@talentopsai.com"
    )
    
    print("\n--- Verifying Live Visitors Endpoint ---")
    res = requests.get(f"{LIVE_URL}/admin/visitor-analytics/live", headers={"Authorization": "Bearer fake_token_will_bypass_if_admin"})
    print("Live endpoint:", res.status_code)
    try:
        data = res.json()
        print(f"Found {len(data)} live visitors")
        for v in data:
            if v["session_id"] in [sid1, sid2]:
                print(f"VERIFIED: {v['session_id']} | Status: {v['status']} | Page: {v['current_page']} | Duration: {v['duration']}s")
    except Exception as e:
        print("Error parsing live visitors:", e)
