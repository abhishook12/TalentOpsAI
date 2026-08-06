import sys
import os
import requests
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
sys.path.append(r"C:\TalentOpsAI\backend")
from app.models.auth_models import User
from app.models.campaigns import Campaign, CampaignRecruiter
from app.database import Base

API_URL = "http://127.0.0.1:8000"

def get_admin_token():
    from app.database import SessionLocal
    from app.services.auth_service import create_access_token
    from app.models.auth_models import User
    
    db = SessionLocal()
    admin = db.query(User).filter(User.email == "admin@talentops.com").first()
    if not admin:
        return "invalid"
    token = create_access_token(data={"sub": str(admin.id)})
    db.close()
    return token

def verify():
    print("Starting 3-Pass Verification for Campaign Limits...\n")
    
    # Setup 55 dummy recipients
    dummy_recipients = [{"email": f"test{i}@test.com"} for i in range(55)]
    
    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Setup Dummy Campaign
    res = requests.post(f"{API_URL}/campaigns", headers=headers, json={
        "name": "Limit Test Campaign",
        "from_email": "admin@talentops.com",
        "status": "draft"
    })
    cid = res.json().get("campaign_id")
    
    for i in range(1, 4):
        print(f"--- PASS {i} ---")
        
        # Test 1: Preflight (should return RECIPIENT_LIMIT_EXCEEDED)
        res = requests.post(f"{API_URL}/campaigns/{cid}/prepare-preview", headers=headers, json={
            "name": "Limit Test Campaign",
            "from_email": "admin@talentops.com",
            "subject": "Test",
            "body": "Test",
            "recipients": dummy_recipients
        })
        
        if not res.ok:
            print(f"FAIL: /prepare-preview crashed: {res.text}")
            sys.exit(1)
            
        data = res.json()
        limit_error = next((e for e in data.get("errors", []) if e.get("code") == "RECIPIENT_LIMIT_EXCEEDED"), None)
        if not limit_error:
            print(f"FAIL: Did not get RECIPIENT_LIMIT_EXCEEDED error. Got: {data.get('errors')}")
            sys.exit(1)
            
        print("SUCCESS: Preflight correctly blocked the campaign and returned RECIPIENT_LIMIT_EXCEEDED error.")
        
        # Test 2: Start endpoint (should return 400)
        res2 = requests.post(f"{API_URL}/campaigns/{cid}/start", headers=headers)
        if res2.status_code != 400 or "Max 50 recipients" not in res2.text:
            print(f"FAIL: /start did not block correctly. Code: {res2.status_code}, Body: {res2.text}")
            sys.exit(1)
            
        print("SUCCESS: Start endpoint safely rejected the massive campaign payload.")
        time.sleep(0.5)
        
    print("\nFINAL RESULT: 3/3 Passes completed successfully. Campaign Limit is verified.")
    
    # Cleanup
    db = SessionLocal()
    db.query(CampaignRecruiter).filter(CampaignRecruiter.campaign_id == cid).delete()
    db.query(Campaign).filter(Campaign.campaign_id == cid).delete()
    db.commit()
    db.close()

if __name__ == "__main__":
    verify()
